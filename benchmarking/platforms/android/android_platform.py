#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import re
import shlex
import time

from platforms.platform_base import PlatformBase
from utils.arg_parse import getParser, getArgs
from utils.custom_logger import getLogger

getParser().add_argument("--android_dir", default="/data/local/tmp/",
    help="The directory in the android device all files are pushed to.")


class AndroidPlatform(PlatformBase):
    def __init__(self, tempdir, adb):
        super(AndroidPlatform, self).__init__(
            tempdir, getArgs().android_dir, adb)
        platform = adb.shell(
            ['getprop', 'ro.product.model'], default="").strip() + \
            '-' + \
            adb.shell(
            ['getprop', 'ro.build.version.release'], default="").strip() + \
            '-' + \
            adb.shell(['getprop', 'ro.build.version.sdk'], default="").strip()
        self.type = "android"
        self.setPlatform(platform)
        self.setPlatformHash(adb.device)
        self._setLogCatSize()
        if getArgs().set_freq:
            self.util.setFrequency(getArgs().set_freq)

    def _setLogCatSize(self):
        repeat = True
        size = 131072
        while (repeat and size > 256):
            repeat = False
            ret = self.util.logcat("-G", str(size) + "K")
            if ret.find("failed to") >= 0:
                repeat = True
                size = int(size / 2)

    def rebootDevice(self):
        self.util.reboot()
        self.waitForDevice(180)

        # Need to wait a bit more after the device is rebooted
        time.sleep(20)
        # may need to set log size again after reboot
        self._setLogCatSize()
        if getArgs().set_freq:
            self.util.setFrequency(getArgs().set_freq)

    def runCommand(self, cmd):
        return self.util.shell(cmd)

    def runBenchmark(self, cmd, *args, **kwargs):
        if not isinstance(cmd, list):
            cmd = shlex.split(cmd)
        self.util.logcat('-b', 'all', '-c')
        log_to_screen_only = 'log_to_screen_only' in kwargs and \
            kwargs['log_to_screen_only']
        android_kwargs = {}
        if "platform_args" in kwargs:
            platform_args = kwargs["platform_args"]
            if "taskset" in platform_args:
                taskset = platform_args["taskset"]
                cmd = ["taskset", taskset] + cmd
                del platform_args["taskset"]
            if "sleep_before_run" in platform_args:
                sleep_before_run = str(platform_args["sleep_before_run"])
                cmd = ["sleep", sleep_before_run, "&&"] + cmd
            if "power" in platform_args and platform_args["power"]:
                # launch settings page to prevent the phone
                # to go into sleep mode
                self.util.shell(["am", "start", "-a",
                                "android.settings.SETTINGS"])
                time.sleep(1)
                cmd = ["nohup"] + ["sh", "-c", "'" + " ".join(cmd) + "'"] + \
                    [">", "/dev/null", "2>&1"]
                log_to_screen_only = True
                android_kwargs["non_blocking"] = True
                del platform_args["power"]
            if "timeout" in platform_args and platform_args["timeout"]:
                android_kwargs["timeout"] = platform_args["timeout"]
                del platform_args["timeout"]
        log_screen = self.util.shell(cmd, **android_kwargs)
        log_logcat = ""
        if not log_to_screen_only:
            log_logcat = self.util.logcat('-d')
        return log_screen + log_logcat

    def collectMetaData(self, info):
        meta = super(AndroidPlatform, self).collectMetaData(info)
        meta['platform_hash'] = self.platform_hash
        return meta

    def killProgram(self, program):
        res = self.util.shell(["ps", "|", "grep", program])
        results = res.split("\n")
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
        ls = None
        while ls is None and count < num:
            ls = self.util.shell(['ls', self.tgt_dir])
            time.sleep(period)
        if ls is None:
            getLogger().error("Cannot reach device {} ({}) after {}.".
                              format(self.platform, self.platform_hash,
                                     timeout))
