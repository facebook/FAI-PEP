##############################################################################
# Copyright 2023-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

# pyre-unsafe

import logging
import threading
import time
from typing import Dict, List

import pkg_resources
from platforms.android.adb import ADB

from utils.custom_logger import getLogger
from utils.utilities import setRunKilled


class ThermalException(Exception):
    pass


# This class runs a thread which periodically executes the thermal monitor
# script on device. If the script return output indicating the script
# killed a benchmark it will call setRunKilled and log output
# to the benchmark.
class ThermalMonitor:
    def __init__(
        self,
        log_handle: List[str],
        adb: ADB,
        thermal_monitor_config: Dict[str, str],
        pattern: str,
        delay: float = 10.0,
        lead_in_delay: float = 15.0,
    ):
        """
        If thermal monitoring is specified for a device, load the config.
        Config must be in the form
        <platform.model>: {
            'script': <path to script to run>
            'trip_temp_expr': <an expression evaluated to trip temp>
            'temp_probe': <the file which will be polled to monitor temperature>
        }
        Script will be pushed to the platform and run every delay seconds.
        pattern: string - pattern of program to match
        lead_in_delay: int - delay before starting monitoring loop
        """
        self.log_handle = log_handle
        self.thermal_monitor_config = thermal_monitor_config
        self.adb = adb
        self.initialized = False
        self.thermal_monitor_script_dst = "/data/local/tmp/thermal_monitor.sh"
        if thermal_monitor_config:
            try:
                self.log(f"Thermal config found for device {adb.device}.")
                self.trip_temp_expr = self.thermal_monitor_config["trip_temp_expr"]
                self.temp_probe = self.thermal_monitor_config["temp_probe"]
                self.push_thermal_script()
                self.initialized = True
            except Exception:
                self.log(
                    f"WARNING! Thermal monitoring was not properly initialized for device {self.adb.device}.",
                    logging.CRITICAL,
                    exc_info=True,
                )

        self.pattern = pattern
        self.delay = delay
        self.lead_in_delay = lead_in_delay
        self.thermal_trip_pattern = "THERMAL LIMIT EXCEEDED! STOPPING PROCESSES"
        self.no_matching_process_pattern = (
            "No processes running matching pattern found. Stopping."
        )
        self.monitor = None
        self.running = False

    # Start thermal monitoring loop which will run the script each delay seconds.
    def __enter__(self):
        if self.initialized:
            self.running = True
            self.monitor = threading.Thread(target=self.start_thermal_monitoring)
            self.monitor.start()
            self.log(
                f"Thermal monitoring started. {self.trip_temp_expr=} {self.temp_probe=} {self.pattern=} {self.delay=}"
            )

    def __exit__(self, type, value, traceback):
        if self.initialized:
            if self.running is True:
                self.running = False
            self.monitor.join(timeout=5.0)
            self.log("Exiting thermal monitor.")

    # Set benchmark status to killed to end the process and inform user the benchmark was stopped.
    def thermal_stop_action(self):
        setRunKilled(True)

    # Push thermal monitoring script to the device.
    def push_thermal_script(self):
        thermal_monitor_script = self.thermal_monitor_config.get("script")
        thermal_monitor_script_loc = pkg_resources.resource_filename(
            "aibench", thermal_monitor_script
        )

        self.adb.push(thermal_monitor_script_loc, self.thermal_monitor_script_dst)
        self.adb.shell(["chmod", "+x", self.thermal_monitor_script_dst], silent=True)

    # Main loop for the monitoring thread. Sets environment variables and runs thermal monitoring script.
    def start_thermal_monitoring(self):
        lead_in = True
        while self.running:
            if lead_in:
                time.sleep(self.lead_in_delay)
                lead_in = False
            cmd = (
                f'export TRIP_TEMP="{self.trip_temp_expr}"'
                f' && export TEMP_PROBE="{self.temp_probe}"'
                f' && export PROG_PATTERN="{self.pattern}"'
                f' && export THERMAL_TRIP_PATTERN="{self.thermal_trip_pattern}"'
                f' && export NO_MATCHING_PROCESS_PATTERN="{self.no_matching_process_pattern}"'
                f" && {self.thermal_monitor_script_dst}"
            ).split(" ")
            result = self.adb.shell(cmd, silent=True)
            if result:
                self.log("\n".join(result))
            if self.no_matching_process_pattern in result:
                self.running = False
                self.log("Process pattern not matched, exiting thermal monitor.")
                break
            elif self.thermal_trip_pattern in result:
                self.log(
                    "\n\n## CRITICAL TEMPERATURE REACHED ON DEVICE! PROCESSES HAVE BEEN SHUT DOWN. ##\n\n"
                )
                self.thermal_stop_action()
            time.sleep(self.delay)

    # log to logger and append to result for output to benchmark.
    def log(self, msg: str, level=logging.INFO, exc_info=False):
        getLogger().log(
            level,
            "\n".join(["Thermal monitoring:\t" + string for string in msg.split("\n")]),
            exc_info=exc_info,
        )
        self.log_handle += ["Thermal monitoring:\t" + string for string in msg]
