#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import json
import os
import re
import shlex
import shutil
import time
from six import string_types

from platforms.platform_base import PlatformBase
from utils.custom_logger import getLogger
from utils.utilities import getRunStatus, setRunStatus
from profilers.profilers import getProfilerByUsage


class AndroidPlatform(PlatformBase):
    def __init__(self, tempdir, adb, args, usb_controller=None):
        super(AndroidPlatform, self).__init__(
            tempdir, args.android_dir, adb, args.hash_platform_mapping,
            args.device_name_mapping)
        self.args = args
        self.rel_version = adb.shell(['getprop', 'ro.build.version.release'], default="")[0].strip()
        self.build_version = adb.shell(['getprop', 'ro.build.version.sdk'], default="")[0].strip()
        platform = adb.shell(['getprop', 'ro.product.model'], default="")[0].strip() + \
            '-' + self.rel_version + '-' + self.build_version
        self.platform_abi = adb.shell(['getprop ro.product.cpu.abi'], default="")[0].strip()
        self.os_version = "{}-{}".format(self.rel_version, self.build_version)
        self.type = "android"
        self.setPlatform(platform)
        self.setPlatformHash(adb.device)
        self.usb_controller = usb_controller
        self._setLogCatSize()
        self.app = None
        if self.args.set_freq:
            self.util.setFrequency(self.args.set_freq)

    def getKind(self):
        if self.platform_model and self.platform_os_version:
            return "{}-{}".format(self.platform_model, self.platform_os_version)
        return self.platform

    def getOS(self):
        return "Android {} sdk {}".format(self.rel_version, self.build_version)

    def _setLogCatSize(self):
        repeat = True
        size = 131072
        while (repeat and size > 256):
            repeat = False
            # We know this command may fail. Avoid propogating this
            # failure to the upstream
            success = getRunStatus()
            ret = self.util.logcat("-G", str(size) + "K")
            setRunStatus(success, overwrite=True)
            if len(ret) > 0 and ret[0].find("failed to") >= 0:
                repeat = True
                size = int(size / 2)

    def fileExistsOnPlatform(self, files):
        if isinstance(files, string_types):
            exists=self.util.shell("test -e {} && echo True || echo False".format(files).split(" "))
            if "True" not in exists:
                return False
            return True
        elif isinstance(files, list):
            for f in files:
                if not self.fileExistsOnPlatform(f):
                    return False
            return True
        raise TypeError("fileExistsOnPlatform takes either a string or list of strings.")

    def preprocess(self, *args, **kwargs):
        assert "programs" in kwargs, "Must have programs specified"

        programs = kwargs["programs"]
        benchmark = kwargs["benchmark"]

        # find the first zipped app file
        assert "program" in programs, "program is not specified"

        if "platform" in benchmark["model"] and \
                benchmark["model"]["platform"].startswith("android"):
            if "app" in benchmark["model"]:
                self.app = benchmark["model"]["app"]

        if not self.app:
            if "intent.txt" in programs:
                # temporary to rename the program with adb suffix
                with open(programs["intent.txt"], "r") as f:
                    self.app = json.load(f)
            else:
                return

        # Uninstall if exist
        package = self.util.shell(["pm", "list", "packages",
                                   self.app["package"]])
        if len(package) > 0 and \
                package[0].strip() == "package:" + self.app["package"]:
            self.util.shell(["pm", "uninstall", self.app["package"]])
        # temporary fix to allow install apk files
        if not programs["program"].endswith(".apk"):
            new_name = programs["program"] + ".apk"
            shutil.copyfile(programs["program"], new_name)
            programs["program"] = new_name
        self.util.run(["install", programs["program"]])

        del programs["program"]

    def rebootDevice(self):
        self.util.reboot()
        self.waitForDevice(180)

        # Need to wait a bit more after the device is rebooted
        time.sleep(20)
        # may need to set log size again after reboot
        self._setLogCatSize()
        if self.args.set_freq:
            self.util.setFrequency(self.args.set_freq)

    def runBenchmark(self, cmd, *args, **kwargs):
        if not isinstance(cmd, list):
            cmd = shlex.split(cmd)

        # meta is used to store any data about the benchmark run
        # that is not the output of the command
        meta = {}

        # We know this command may fail. Avoid propogating this
        # failure to the upstream
        success = getRunStatus()
        self.util.logcat('-b', 'all', '-c')
        setRunStatus(success, overwrite=True)
        if self.app:
            log, meta = self.runAppBenchmark(cmd, *args, **kwargs)
        else:
            log, meta = self.runBinaryBenchmark(cmd, *args, **kwargs)
        return log, meta

    def runAppBenchmark(self, cmd, *args, **kwargs):
        arguments = self.getPairedArguments(cmd)
        argument_filename = os.path.join(self.tempdir, "benchmark.json")
        arguments_json = json.dumps(arguments, indent=2, sort_keys=True)
        with open(argument_filename, "w") as f:
            f.write(arguments_json)
        tgt_argument_filename = os.path.join(self.tgt_dir, "benchmark.json")
        activity = os.path.join(self.app["package"], self.app["activity"])
        self.util.push(argument_filename, tgt_argument_filename)
        platform_args = {}
        if "platform_args" in kwargs:
            platform_args = kwargs["platform_args"]
            if "power" in platform_args and platform_args["power"]:
                platform_args["non_blocking"] = True
                self.util.shell(["am", "start", "-S", activity])
                return []
            if platform_args.get("enable_profiling",False):
                getLogger().warn("Profiling for app benchmarks is not implemented.")

        patterns = []
        pattern = re.compile(
            r".*{}.*{}.*BENCHMARK_DONE".format(self.app["package"],
                                               self.app["activity"]))
        patterns.append(pattern)
        pattern = re.compile(
            r".*ActivityManager: Killing .*{}".format(self.app["package"]))
        patterns.append(pattern)
        platform_args["patterns"] = patterns
        self.util.shell(["am", "start", "-S", "-W", activity])
        log_logcat = self.util.run(["logcat"], **platform_args)
        self.util.shell(["am", "force-stop", self.app["package"]])
        return log_logcat

    def runBinaryBenchmark(self, cmd, *args, **kwargs):
        log_to_screen_only = 'log_to_screen_only' in kwargs and \
            kwargs['log_to_screen_only']
        platform_args = {}
        meta = {}
        if "platform_args" in kwargs:
            platform_args = kwargs["platform_args"]
            if "taskset" in platform_args:
                taskset = platform_args["taskset"]
                cmd = ["taskset", taskset] + cmd
                del platform_args["taskset"]
            if "sleep_before_run" in platform_args:
                sleep_before_run = str(platform_args["sleep_before_run"])
                cmd = ["sleep", sleep_before_run, "&&"] + cmd
                del platform_args["sleep_before_run"]
            if "power" in platform_args and platform_args["power"]:
                # launch settings page to prevent the phone
                # to go into sleep mode
                self.util.shell(["am", "start", "-a",
                                "android.settings.SETTINGS"])
                time.sleep(1)
                cmd = ["nohup"] + ["sh", "-c", "'" + " ".join(cmd) + "'"] + \
                    [">", "/dev/null", "2>&1"]
                platform_args["non_blocking"] = True
                del platform_args["power"]
            if platform_args.get("enable_profiling", False):
                # attempt to run with profiling, else fallback to standard run
                try:
                    simpleperf = getProfilerByUsage("android", None, platform=self, model_name=platform_args.get("model_name",None), cmd=cmd)
                    if simpleperf:
                        f = simpleperf.start()
                        output, meta = f.result()
                        if not output or not meta:
                            raise RuntimeError("No data returned from Simpleperf profiler.")
                        log_logcat = []
                        if not log_to_screen_only:
                            log_logcat = self.util.logcat('-d')
                        return output + log_logcat, meta
                # if this has not succeeded for some reason reset run status and run without profiling.
                except Exception as ex:
                    getLogger().exception(f"An error has occurred when running Simpleperf profiler. {ex}")
        log_screen = self.util.shell(cmd, **platform_args)
        log_logcat = []
        if not log_to_screen_only:
            log_logcat = self.util.logcat('-d')
        return log_screen + log_logcat, meta

    def collectMetaData(self, info):
        meta = super(AndroidPlatform, self).collectMetaData(info)
        meta['platform_hash'] = self.platform_hash
        return meta

    def killProgram(self, program):
        basename = os.path.basename(program)
        # if the program doesn't exist, the grep may fail
        # do not update status code
        success = getRunStatus()
        res = self.util.shell(["ps", "|", "grep", basename])
        setRunStatus(success, overwrite=True)
        if len(res) == 0:
            return
        results = res[0].split("\n")
        pattern = re.compile(r"^shell\s+(\d+)\s+")
        for result in results:
            match = pattern.match(result)
            if match:
                pid = match.group(1)
                self.util.shell(["kill", pid])

    def waitForDevice(self, timeout):
        period = int(timeout / 20) + 1
        num = int(timeout / period)
        count = 0
        ls = []
        while len(ls) == 0 and count < num:
            ls = self.util.shell(['ls', self.tgt_dir])
            time.sleep(period)
        if len(ls) == 0:
            getLogger().error("Cannot reach device {} ({}) after {}.".
                              format(self.platform, self.platform_hash,
                                     timeout))
