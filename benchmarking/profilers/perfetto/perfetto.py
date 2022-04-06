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
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

# from platforms.android.android_platform import AndroidPlatform
from profilers.perfetto.perfetto_config import (
    CONFIG_TEMPLATE,
    POWER_CONFIG,
    HEAPPROFD_CONFIG,
    ANDROID_LOG_CONFIG,
    LINUX_FTRACE_CONFIG,
)
from profilers.profiler_base import ProfilerBase
from profilers.utilities import generate_perf_filename, upload_profiling_reports
from utils.custom_logger import getLogger

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


class Perfetto(ProfilerBase):

    CONFIG_FILE = "perfetto.conf"
    DEVICE_DIRECTORY = "/data/local/tmp/perf"
    TRACING_PROPERTY = "persist.traced.enable"
    DEFAULT_TIMEOUT = 5
    BUFFER_SIZE_KB_DEFAULT = 256 * 1024  # 256 megabytes
    BUFFER_SIZE2_KB_DEFAULT = 2 * 1024  # 2 megabytes
    SHMEM_SIZE_BYTES_DEFAULT = (
        8192 * 4096
    )  # Shared memory buffer must be a large multiple of 4096
    SAMPLING_INTERVAL_BYTES_DEFAULT = 4096
    BATTERY_POLL_MS_DEFAULT = 1000
    MAX_FILE_SIZE_BYTES_DEFAULT = 100000000

    def __init__(
        self,
        platform,
        *,
        types=None,
        options=None,
        model_name="benchmark",
    ):
        self.platform = platform
        self.types = types or ["memory"]
        self.options = options or {}
        self.android_version: int = int(platform.rel_version.split(".")[0])
        self.adb = platform.util
        self.valid = True
        self.perfetto_pid = None
        self.all_heaps = (
            f"all_heaps: {self.options.get('all_heaps', 'false')}"
            if self.android_version >= 12
            else ""
        )
        self.basename = generate_perf_filename(model_name, self.adb.device)
        self.trace_file_name = f"{self.basename}.perfetto-trace"
        self.trace_file_device = f"{self.DEVICE_DIRECTORY}/{self.trace_file_name}"
        self.config_file = f"{self.basename}.{self.CONFIG_FILE}"
        self.config_file_device = f"{self.DEVICE_DIRECTORY}/{self.config_file}"
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
            "perfetto",
            "-d",
            "--txt",
            "-c",
            self.config_file_device,
            "-o",
            self.trace_file_device,
        ]
        super(Perfetto, self).__init__(None)

    def __enter__(self):
        self._start()

        return self

    def __exit__(self, type, value, traceback):
        if self.meta == {}:
            self.meta = self._finish()

    def _start(self):
        """Begin Perfetto profiling on platform."""
        try:
            if self.android_version < 10:
                getLogger().error(
                    f"Attempt to run Perfetto on {self.platform.type} {self.platform.rel_version} device {self.adb.device} ignored."
                )
                self.valid = False
                return None

            if not self.is_rooted_device:
                getLogger().error(
                    f"Attempt to run Perfetto on unrooted device {self.adb.device} ignored."
                )
                self.valid = False
                return None

            getLogger().info(f"Collect Perfetto data on device {self.adb.device}")
            self._enablePerfetto()

            # Generate and upload custom config file
            getLogger().info(f"Perfetto profile type(s) = {','.join(self.types)}.")
            self._setup_perfetto_config()
            """
            # Ensure no old instances of perfetto are running on the device
            self.adb.shell(
                ["killall", "perfetto"],
                timeout=DEFAULT_TIMEOUT,
            )
            """

            # call Perfetto
            output = self._perfetto()
            if output != 1 and output[0] != "1":
                self.perfetto_pid = output[0]
            return output
        except Exception:
            self.valid = False
            getLogger().exception("Perfetto profiling could not be started.")
            return None

    def getResults(self):
        if self.valid:
            self.meta = self._finish()

        return self.meta

    def _finish(self):
        no_report_str = "Perfetto profiling reporting could not be completed."
        if not self.valid:
            self._restoreState()
            return {}

        meta = {}
        self.host_output_dir = tempfile.mkdtemp()
        try:
            # if we ran perfetto, signal it to stop profiling
            if self._signalPerfetto():
                getLogger().info(
                    f"Looking for Perfetto data on device {self.adb.device}"
                )
                self._copyPerfDataToHost()
                self._generateReport()
                meta = self._uploadResults()
            else:
                getLogger().error(
                    no_report_str,
                )
        except Exception as e:
            getLogger().exception(
                no_report_str + f" {e}",
                exc_info=True,
            )

            # TODO: remove reboot + sleep once this is done in device manager
            self.adb.reboot()
            time.sleep(10)
            meta = {}
        finally:
            self._restoreState()
            shutil.rmtree(self.host_output_dir)
            self.valid = False  # prevent additional calls

        return meta

    def _uploadResults(self):
        meta = upload_profiling_reports(
            {
                "perfetto_config": os.path.join(self.host_output_dir, self.config_file),
                "perfetto_data": os.path.join(
                    self.host_output_dir, self.trace_file_name
                ),
                # TODO: generate flamegraph here
                "perfetto_report": os.path.join(self.host_output_dir, self.config_file),
            }
        )
        getLogger().info(
            f"Perfetto profiling data uploaded.\nPerfetto Config:\t{meta['perfetto_config']}\nPerfetto Data:  \t{meta['perfetto_data']}\nPerfetto Report:\t{meta['perfetto_report']}"
        )

        return meta

    def _restoreState(self):
        if self.original_SELinux_policy == "enforcing":
            self.adb.shell(
                ["setenforce", "1"],
                timeout=self.DEFAULT_TIMEOUT,
                retry=1,
            )
        if (not self.user_was_root) and self.adb.user_is_root():
            self.adb.unroot()  # unroot only if it was not rooted to start

    def _signalPerfetto(self) -> bool:
        # signal perfetto to stop profiling and await results
        getLogger().info("Stopping Perfetto profiling.")
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

    def _enablePerfetto(self):
        if not self.user_was_root:
            self.adb.root()

        # Set SELinux to permissive mode if not already
        if self.original_SELinux_policy == "enforcing":
            self.adb.shell(
                ["setenforce", "0"],
                timeout=self.DEFAULT_TIMEOUT,
                retry=1,
            )

        # Enable Perfetto if not enabled yet.
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

    def _setup_perfetto_config(
        self,
        *,
        app_name: str = "program",
        config_file_host: Optional[str] = None,
        android_logcat: bool = False,
    ):
        with NamedTemporaryFile() as f:
            if config_file_host is None:
                # Write custom perfetto config
                config_file_host = f.name
                heapprofd_config = ""
                power_config = ""
                linux_process_stats_config = ""
                linux_ftrace_config = ""
                android_log_config = ""
                track_event_config = ""
                buffer_size_kb = self.options.get(
                    "buffer_size_kb", self.BUFFER_SIZE_KB_DEFAULT
                )
                buffer_size2_kb = self.options.get(
                    "buffer_size2_kb", self.BUFFER_SIZE2_KB_DEFAULT
                )
                max_file_size_bytes = self.options.get(
                    "max_file_size_bytes", self.MAX_FILE_SIZE_BYTES_DEFAULT
                )
                if "memory" in self.types:
                    shmem_size_bytes = self.options.get(
                        "shmem_size_bytes", self.SHMEM_SIZE_BYTES_DEFAULT
                    )
                    sampling_interval_bytes = self.options.get(
                        "sampling_interval_bytes", self.SAMPLING_INTERVAL_BYTES_DEFAULT
                    )
                    heapprofd_config = HEAPPROFD_CONFIG.format(
                        all_heaps=self.all_heaps,
                        shmem_size_bytes=shmem_size_bytes,
                        sampling_interval_bytes=sampling_interval_bytes,
                        app_name=app_name,
                    )
                if "battery" in self.types:
                    battery_poll_ms = self.options.get(
                        "battery_poll_ms", self.BATTERY_POLL_MS_DEFAULT
                    )
                    power_config = POWER_CONFIG.format(
                        battery_poll_ms=battery_poll_ms,
                    )
                    linux_ftrace_config = LINUX_FTRACE_CONFIG.format(
                        app_name=app_name,
                    )

                if "cpu" in self.types:
                    getLogger().error(
                        "Error: CPU profiling with perfetto is Not Yet Implemented.",
                    )

                if android_logcat:
                    android_log_config = ANDROID_LOG_CONFIG

                # Generate config file
                config_str = CONFIG_TEMPLATE.format(
                    max_file_size_bytes=max_file_size_bytes,
                    buffer_size_kb=buffer_size_kb,
                    buffer_size2_kb=buffer_size2_kb,
                    android_log_config=android_log_config,
                    power_config=power_config,
                    heapprofd_config=heapprofd_config,
                    linux_process_stats_config=linux_process_stats_config,
                    linux_ftrace_config=linux_ftrace_config,
                    track_event_config=track_event_config,
                )
                f.write(config_str.encode("utf-8"))
                f.flush()

            # Push perfetto config to device
            getLogger().info(
                f"Host config file = {config_file_host},\nDevice config file = {self.config_file_device}."
            )
            self.adb.push(config_file_host, self.config_file_device)

            # Setup permissions for it, to avoid perfetto call failure
            self.adb.shell(["chmod", "777", self.config_file_device])

    def _perfetto(self):
        """Run perfetto on platform with benchmark process id."""
        getLogger().info(f"Calling Perfetto: {self.perfetto_cmd}")
        output = self.platform.util.shell(self.perfetto_cmd)
        getLogger().info(f"Perfetto returned: {output}.")
        startup_time: float = 2.0 if self.all_heaps != "false" else 0.2
        time.sleep(startup_time)  # give it time to spin up
        return output

    def _copyPerfDataToHost(self):
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
