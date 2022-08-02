#!/usr/bin/env python

##############################################################################
# Copyright 2021-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import logging
import os
import shutil
import tempfile
import time
from enum import Enum
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List

# from platforms.android.android_platform import AndroidPlatform
from profilers.perfetto.perfetto_config import PerfettoConfig
from profilers.profiler_base import ProfilerBase
from profilers.utilities import generate_perf_filename, upload_profiling_reports
from utils.custom_logger import getLogger
from utils.utilities import BenchmarkUnsupportedDeviceException

PROCESS_KEY = "perfetto"

"""
Perfetto is a native memory and battery profiling tool for Android OS 10 or better.
It can be used to profile both Android applications and native
processes running on Android. It can profile both Java and C++ code on Android.

Perfetto can be used to profile Android benchmarks as both applications and
binaries. The resulting perf data is used to generate an html report
including a flamegraph (TODO). Both perf data and the report are uploaded to manifold
and the urls are returned as a meta dict which can be updated in the benchmark's meta data.
"""

logger = logging.getLogger(__name__)

perfetto_types_supported: set = {"memory", "battery", "gpu", "cpu"}


def PerfettoAnySupported(types) -> bool:
    return bool(perfetto_types_supported.intersection(types))


def PerfettoAllSupported(types) -> bool:
    return perfetto_types_supported.issuperset(types)


class BatteryState(Enum):
    connected = 0
    disconnected = 1


class Perfetto(ProfilerBase):

    CONFIG_FILE = "perfetto.conf"
    DEVICE_DIRECTORY = "/data/local/tmp/perf"
    DEVICE_TRACE_DIRECTORY = "/data/misc/perfetto-traces"
    TRACING_PROPERTY = "persist.traced.enable"
    DEFAULT_TIMEOUT = 5
    BUFFER_SIZE_KB_DEFAULT = 256 * 1024  # 256 megabytes
    BUFFER_SIZE2_KB_DEFAULT = 2 * 1024  # 2 megabytes
    SHMEM_SIZE_BYTES_DEFAULT = (
        8192 * 4096
    )  # Shared memory buffer must be a large multiple of 4096
    SAMPLING_INTERVAL_BYTES_DEFAULT = 4096
    DUMP_INTERVAL_MS_DEFAULT = 1000
    BATTERY_POLL_MS_DEFAULT = 1000
    CPU_POLL_MS_DEFAULT = 1000
    MAX_FILE_SIZE_BYTES_DEFAULT = 100000000

    def __init__(
        self,
        platform,
        cmd: List,
        *,
        model_name="benchmark",
        types=None,
        options=None,
    ):
        self.platform = platform
        self.types = types or ["memory"]
        self.options = options or {}
        self.android_version: int = int(platform.rel_version.split(".")[0])
        self.adb = platform.util
        self.valid = False
        self.restoreState = False
        self.perfetto_pid = None

        if self.android_version < 12 and self.options.get("all_heaps", False):
            self.options.all_heaps = False
        self.perfetto_config = PerfettoConfig(
            self.types, self.options, app_name=os.path.basename(cmd[0])
        )
        self.basename = generate_perf_filename(model_name, self.platform.platform_hash)
        self.trace_file_name = f"{self.basename}.perfetto-trace"
        self.trace_file_device = f"{self.DEVICE_TRACE_DIRECTORY}/{self.trace_file_name}"
        self.config_file = f"{self.basename}.{self.CONFIG_FILE}"
        self.config_file_device = f"{self.DEVICE_DIRECTORY}/{self.config_file}"
        self.config_file_host = None
        self.data_file = f"{self.basename}.data.json"
        self.report_file = f"{self.basename}.txt"  # f"{self.basename}.html"
        self.user_home = str(Path.home())
        self.host_binary_location = f"{self.user_home}/android"
        self.host_output_dir = ""
        self.meta = {}
        self.is_rooted_device = self.adb.isRootedDevice()
        self.user_was_root = self.adb.user_is_root() if self.is_rooted_device else False
        self.original_SELinux_policy = (
            self.adb.shell(
                ["getenforce"],
                default=[""],
                timeout=self.DEFAULT_TIMEOUT,
            )[0]
            .strip()
            .lower()
        )
        self.perfetto_cmd = [
            "cat",
            self.config_file_device,
            "|",
            "perfetto",
            "-d",
            "--txt",
            "-c",
            "-",
            "-o",
            self.trace_file_device,
        ]

        # This is a generic path to disconnect battery charing on many Android devices.
        # Going forward, it may be necessary to override this default mechanism on some devices.
        self.battery_disconnected_path = "/sys/class/power_supply/battery/input_suspend"
        self.battery_state: BatteryState = BatteryState.connected

        super(Perfetto, self).__init__(None)

    def __enter__(self):
        self._start()

        return self

    def __exit__(self, type, value, traceback):
        self._finish()

    def _start(self):
        """Begin Perfetto profiling on platform."""
        self.valid = False

        # Validation
        if self.android_version < 10:
            raise BenchmarkUnsupportedDeviceException(
                f"Attempt to run perfetto on {self.platform.type} {self.platform.rel_version} device {self.platform.device_label} ignored."
            )

        if self.is_rooted_device:
            if not self.user_was_root:
                self.adb.root()

        if "battery" in self.types:
            if self.is_rooted_device:
                if not self._hasBattery():
                    raise BenchmarkUnsupportedDeviceException(
                        f"Cannot run perfetto battery profiling on device {self.platform.device_label} without a (supported) battery."
                    )
            else:
                raise BenchmarkUnsupportedDeviceException(
                    f"Perfetto battery profiling is unsupported on unrooted device {self.platform.device_label}."
                )
        try:
            getLogger().info(
                f"Collect perfetto data on device {self.platform.device_label}."
            )
            self._setStateForPerfetto()

            # Generate and upload custom config file
            getLogger().info(f"Perfetto profile type(s) = {', '.join(self.types)}.")
            self._setupPerfettoConfig()

            # call Perfetto
            output = self._perfetto()
        except Exception as e:
            raise RuntimeError(f"Perfetto profiling failed to start:\n{e}.")
        else:
            if output == 1 or output == [] or output[0] == "1":
                raise RuntimeError("Perfetto profiling could not be started.")

            self.perfetto_pid = output[0]
            self.valid = True
            return output

    def getResults(self):
        if self.valid:
            self._finish()

        return self.meta

    def _finish(self):
        no_report_str = "Perfetto profiling reporting could not be completed."

        try:
            if not self.valid:
                return

            # if we ran perfetto, signal it to stop profiling
            if self._signalPerfetto():
                getLogger().info(
                    f"Looking for Perfetto data on device {self.platform.device_label}."
                )
                self._copyPerfettoDataToHost()
                self._generateReport()
                self.meta.update(self._uploadResults())
            else:
                getLogger().error(
                    no_report_str,
                )
        except Exception:
            getLogger().exception(
                no_report_str,
            )

            # TODO: remove reboot + sleep once this is done in device manager
            self.adb.reboot()
            time.sleep(10)
        finally:
            self._restoreState()
            shutil.rmtree(self.host_output_dir, ignore_errors=True)
            self.valid = False  # prevent additional calls

    def _hasBattery(self):
        return self.adb.getBatteryProp("present") == "1"

    def _setBatteryState(self, state: BatteryState):
        cmd_exists = ["ls", self.battery_disconnected_path]
        cmd_update = ["echo", str(state.value), ">", self.battery_disconnected_path]
        try:
            if self.adb.shell(cmd_exists, retry=1, silent=True) == [
                self.battery_disconnected_path
            ]:
                self.adb.shell(cmd_update, retry=1, silent=True)
                getLogger().info(
                    f"Battery {state.name} for charging on device {self.platform.device_label}."
                )
                self.battery_state = state
            else:
                # this should have been caught by the battery check, but just in case
                raise BenchmarkUnsupportedDeviceException(
                    f"Battery disconnect not supported for device {self.platform.device_label}."
                )
        except Exception:
            # alert if we disconnected but cannot now reconnect
            error = f"Battery not {state.name} for charging on device {self.platform.device_label}."
            if state == BatteryState.connected:
                getLogger().critical(error)
            else:
                getLogger().exception(error)

    def _uploadConfig(self, config_file):
        self.meta = upload_profiling_reports(
            {
                "perfetto_config": config_file,
            }
        )
        getLogger().info(
            f"Perfetto config file uploaded.\nPerfetto Config:\t{self.meta['perfetto_config']}"
        )

    def _uploadResults(self):
        meta = upload_profiling_reports(
            {
                "perfetto_data": os.path.join(
                    self.host_output_dir, self.trace_file_name
                ),
                # TODO: generate flamegraph here
                "perfetto_report": os.path.join(self.host_output_dir, self.config_file),
            }
        )
        getLogger().info(
            f"Perfetto profiling data uploaded.\nPerfetto Data:  \t{meta['perfetto_data']}\nPerfetto Report:\t{meta['perfetto_report']}"
        )

        return meta

    def _restoreState(self):
        """Restore original device state if necessary"""
        if self.battery_state == BatteryState.disconnected:
            # restore battery charging
            self._setBatteryState(BatteryState.connected)

        if self.restoreState:
            if self.original_SELinux_policy == "enforcing":
                self.adb.shell(
                    ["setenforce", "1"],
                    timeout=self.DEFAULT_TIMEOUT,
                    retry=1,
                )

        if (not self.user_was_root) and self.adb.user_is_root():
            self.adb.unroot()  # unroot only if it was not rooted to start

        self.restoreState = False

    def _signalPerfetto(self) -> bool:
        # signal perfetto to stop profiling and await results
        getLogger().info("Stopping perfetto profiling.")
        result = None
        if self.perfetto_pid is not None:
            sigint_cmd = [
                "kill",
                "-SIGINT",
                self.perfetto_pid,
                "&&",
                "wait",
                self.perfetto_pid,
            ]
            sigterm_cmd = ["kill", "-SIGTERM", self.perfetto_pid]
        else:
            sigint_cmd = ["pkill", "-SIGINT", "perfetto"]
            sigterm_cmd = ["pkill", "-SIGTERM", "perfetto"]

        cmd = sigint_cmd
        try:
            # Wait for Perfetto to finish gracefully
            getLogger().info("Running '" + " ".join(cmd) + "'.")
            result = self.adb.shell(
                sigint_cmd,
                timeout=30,
                retry=1,
                silent=True,
            )
            if self.perfetto_pid is None:
                time.sleep(6.0)
            return True
        except Exception as e:
            getLogger().exception(
                f"Perfetto did not respond to SIGINT. Terminating. {e}."
            )
            cmd = sigterm_cmd
            result = self.adb.shell(
                cmd,
                timeout=10,
            )
            return False
        finally:
            getLogger().info(f"Running '{' '.join(cmd)}' returned {result}.")

    def _setStateForPerfetto(self):
        if self.is_rooted_device:
            # Set SELinux to permissive mode if not already
            if self.original_SELinux_policy == "enforcing":
                self.adb.shell(
                    ["setenforce", "0"],
                    timeout=self.DEFAULT_TIMEOUT,
                    retry=1,
                )
                self.restoreState = True

            if "battery" in self.types:
                # disable battery charging
                self._setBatteryState(BatteryState.disconnected)

        # Enable Perfetto if not yet enabled.
        getprop_tracing_enabled = self.adb.getprop(
            self.TRACING_PROPERTY,
            default=["0"],
            timeout=self.DEFAULT_TIMEOUT,
        )
        perfetto_enabled: str = (
            getprop_tracing_enabled if getprop_tracing_enabled else "0"
        )
        if not perfetto_enabled.startswith("1"):
            self.adb.setprop(
                self.TRACING_PROPERTY,
                "1",
                timeout=self.DEFAULT_TIMEOUT,
            )

    def _setupPerfettoConfig(
        self,
    ):
        config_str = self.perfetto_config.GeneratePerfettoConfig()
        with NamedTemporaryFile() as f:
            # Write custom perfetto config
            f.write(config_str.encode("utf-8"))
            f.flush()

            # Save away the config file
            self.host_output_dir = tempfile.mkdtemp()
            self.config_file_host = os.path.join(self.host_output_dir, self.config_file)
            shutil.copy(f.name, self.config_file_host)
            self._uploadConfig(self.config_file_host)

        # Push perfetto config to device
        getLogger().info(
            f"Host config file = {self.config_file_host},\nDevice config file = {self.config_file_device}."
        )
        self.adb.push(self.config_file_host, self.config_file_device)

        # Setup permissions for it, to avoid perfetto call failure
        self.adb.shell(["chmod", "777", self.config_file_device])

    def _perfetto(self):
        """Run perfetto on platform with benchmark process id."""
        getLogger().info(f"Calling perfetto: {self.perfetto_cmd}")
        output = self.platform.util.shell(
            self.perfetto_cmd, retry=1
        )  # Don't retry due to risk of leaving 2 copies running
        getLogger().info(f"Perfetto returned: {output}.")

        # longer delay if all_heaps is specified
        startup_time: float = 2.0 if self.options.get("all_heaps", False) else 0.2
        time.sleep(startup_time)  # give perfetto time to spin up
        return output

    def _copyPerfettoDataToHost(self):
        self.platform.moveFilesFromPlatform(
            os.path.join(self.trace_file_device),
            os.path.join(self.host_output_dir),
        )
        self.platform.moveFilesFromPlatform(
            os.path.join(self.config_file_device),
            os.path.join(self.host_output_dir),
        )

    def _generateReport(self):
        """Generate an html report from perfetto data."""
        # TODO: implement
