#!/usr/bin/env python

# pyre-unsafe

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

from bridge.file_storage.download_files.file_downloader import FileDownloader
from profilers.perfetto.perfetto_config import PerfettoConfig
from profilers.profiler_base import ProfilerBase
from profilers.utilities import generate_perf_filename, upload_output_files
from utils.custom_logger import getLogger
from utils.subprocess_with_logger import processRun
from utils.utilities import (
    BenchmarkInvalidBinaryException,
    BenchmarkUnsupportedDeviceException,
)

PROCESS_KEY = "perfetto"

"""
Perfetto is a native memory and battery profiling tool for Android OS 10 or better.
It can be used to profile both Android applications and native
processes running on Android. It can profile both Java and C++ code on Android.

Perfetto can be used to profile Android benchmarks of binaries. The resulting perf data can be opened and interactively viewed using
//https://ui.perfetto.dev/, including a flamegraph (TODO: generate an html report directly). The config file and resulting perfetto
data are uploaded to the cloud. The urls are returned as a dict and added to the benchmark's meta data.
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
        cmd: List[str],
        *,
        model_name="benchmark",
        types=None,
        options=None,
    ):
        self.platform = platform
        self.cmd = cmd
        self.types = types or ["memory"]
        self.options = options or {}
        self.android_version: int = int(platform.rel_version.split(".")[0])
        self.adb = platform.util
        self.valid = False
        self.restoreState = False
        self.perfetto_pid = None
        self.app_path = _getAppPath(cmd, "program")
        self.perfetto_config = PerfettoConfig(
            self.types, self.options, app_name=self.app_path
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

        self.perfetto_path = "perfetto"
        self.advanced_support = self.android_version >= 12
        self.min_ver = int(self.options.get("min_ver", 11))
        if self.android_version < self.min_ver:
            self._init_sideloaded_binary()  # updates self.perfetto_path and self.advanced_support if successful

        self.options["all_heaps"] = self.advanced_support and self.options.get(
            "all_heaps", False
        )
        self.all_heaps_config = (
            "            all_heaps: true\n"
            if self.options.get("all_heaps", False)
            else ""
        )
        self.perfetto_cmd = [
            "cat",
            self.config_file_device,
            "|",
            self.perfetto_path,
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

    def _init_sideloaded_binary(self):
        """
        Verify that perfetto is available on the host, or download it, then copy perfetto onto the mobile device.
        This can throw an exception if the perfetto binary is unexpectedly not found on the host machine
        and must be caught and logged here. We will then default to the OS installed perfetto or give a version
        error if OS version < 10.

        Updates self.perfetto_path and sets self.advanced_support if successful.
        """
        binary_folders = {
            "armeabi-v7a": "arm",
            "arm64-v8a": "arm64",
            "x86": "x86",
            "x86_64": "x86_64",
        }
        self.binary_folder = binary_folders[self.platform.platform_abi]
        self.user_home = str(Path.home())
        self.host_perfetto_folder = os.path.join(self.user_home, "android/perfetto")
        self.host_perfetto_location = os.path.join(
            self.host_perfetto_folder, self.binary_folder, "perfetto"
        )

        try:
            if self._existsOrDownloadPerfetto():
                self._copyPerfetto()
                self.advanced_support = True
        except Exception:
            getLogger().exception("Perfetto binary could not be copied to the device.")

    def _existsOrDownloadPerfetto(self):
        """
        Using an advanced version of the perfetto binary (built from Android OS 12-based sources or better)
        via "sideloading" allows us to take advantage of the latest advanced features and bug fixes.

        If a suitable built version of the perfetto OS 12 binary already exists on the host server, use it.

        Otherwise, attempt to download it if possible.

            1. Only suuported platforms are attempted (currently arm or arm64)
            2. FileDownloader class must have a "default" implementation

        Otherwise, return False and just use the native perfetto binary from the installed device OS.

        An exception will be raised if this should work (i.e., valid platform and implementation) but doesn't.
        """
        if not os.path.exists(self.host_perfetto_location):
            if self.binary_folder not in ("arm", "arm64"):
                # Currently these are the only flavors we support
                getLogger().info(
                    "Cannot download Perfetto.zip: Perfetto.zip doesn't support {self.binary_folder}."
                )
                return False

            try:
                profiling_files_downloader = FileDownloader("default").getDownloader()
            except Exception:
                getLogger().exception(
                    "Cannot download Perfetto.zip: FileDownloader not implemented."
                )
                return False

            getLogger().info(
                "Perfetto binary cannot be found on the host machine. Attempting to download."
            )
            tmpdir = tempfile.mkdtemp()
            filename = os.path.join(tmpdir, "perfetto.zip")
            profiling_files_downloader.downloadFile(file=filename)

            if not os.path.isdir(self.host_perfetto_folder):
                os.makedirs(self.host_perfetto_folder)
            output, err = processRun(
                ["unzip", "-o", filename, "-d", self.host_perfetto_folder]
            )
            if err:
                raise RuntimeError(
                    f"perfetto archive {filename} was not able to be extracted to {self.host_perfetto_folder}"
                )
            if not os.path.exists(self.host_perfetto_location):
                raise RuntimeError(
                    f"Perfetto was not extracted to the expected location {self.host_perfetto_location}."
                    f"Please confirm that it is available for {self.binary_folder}."
                )

        return True

    def _copyPerfetto(self):
        """Check if perfetto binary is on device, if not, copy."""
        remote_binary = os.path.join(self.platform.tgt_dir, "perfetto")
        if not (self.platform.fileExistsOnPlatform(remote_binary)):
            getLogger().info("Copying perfetto to device")
            self.platform.copyFilesToPlatform(
                self.host_perfetto_location,
                target_dir=self.platform.tgt_dir,
                copy_files=True,
            )

            # Setup permissions for it, to avoid perfetto call failure
            self.adb.shell(["chmod", "777", remote_binary])

        self.perfetto_path = remote_binary

    def __enter__(self):
        self._start()

        return self

    def __exit__(self, type, value, traceback):
        self._finish()

    def _validate(self):
        if self.android_version < 10 and not self.advanced_support:
            raise BenchmarkUnsupportedDeviceException(
                f"Attempt to run perfetto on {self.platform.type} {self.platform.rel_version} device {self.platform.device_label} ignored."
            )

        if "memory" in self.types:
            # perfetto has stopped supporting Android 10 for memory profiling!
            if self.android_version < 10:  # TODO: < 11 and not self.advanced_support:
                raise BenchmarkUnsupportedDeviceException(
                    f"Attempt to run perfetto memory profiling on {self.platform.type} {self.platform.rel_version} device {self.platform.device_label} ignored."
                )

            filename = os.path.basename(self.app_path)
            if "#" in filename:
                raise BenchmarkInvalidBinaryException(
                    f"Cannot run perfetto memory profiling on binary filename '{filename}' containing '#'."
                )

            output = self.adb.shell(["file", self.app_path])
            getLogger().info(f"file {self.app_path} returned '{output}'.")

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

    def _start(self):
        """Begin Perfetto profiling on platform."""
        self.valid = False

        if self.is_rooted_device and not self.user_was_root:
            self.adb.root()

        self._validate()
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
            if output == 1 or output == [] or output[-1] == "1":
                raise RuntimeError("Perfetto profiling could not be started.")

            # pid is the last "line" of perfetto output (the only line in release builds)
            self.perfetto_pid = output[-1]
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
                self.meta["output_files"].update(self._uploadResults())
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
        meta = upload_output_files({"Perfetto Config": config_file})
        getLogger().info(
            f"Perfetto config file uploaded.\nPerfetto Config:\t{meta['Perfetto Config']}"
        )
        self.meta = {"output_files": meta}

    def _uploadResults(self):
        meta = upload_output_files(
            {
                "Perfetto Data": os.path.join(
                    self.host_output_dir, self.trace_file_name
                )
                # TODO: generate flamegraph here
            }
        )
        getLogger().info(
            f"Perfetto profiling data uploaded.\nPerfetto Data:  \t{meta['Perfetto Data']}"
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
        config_str = self.perfetto_config.GeneratePerfettoConfig(
            advanced_support=self.advanced_support
        )
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


def _getAppPath(args: List[str], default: str) -> str:
    """App path will be the first non env-setting string."""
    # TODO: externalize this method so it can be used elsewhere
    app_path = default
    for arg in args:
        if "=" not in arg:
            app_path = arg
            break

    return app_path
