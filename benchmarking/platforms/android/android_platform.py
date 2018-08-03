#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import os
import re
import shlex
import time

from platforms.platform_base import PlatformBase
from six import string_types
from utils.arg_parse import getArgs
from utils.custom_logger import getLogger


class AndroidPlatform(PlatformBase):
    def __init__(self, tempdir, adb):
        super(AndroidPlatform, self).__init__()
        self.adb = adb
        platform = adb.shell(
            ['getprop', 'ro.product.model'], default="").strip() + \
            '-' + \
            adb.shell(
            ['getprop', 'ro.build.version.release'], default="").strip() + \
            '-' + \
            adb.shell(['getprop', 'ro.build.version.sdk'], default="").strip()
        self.type = "android"
        self.setPlatform(platform)
        self.platform_hash = adb.device
        self._setLogCatSize()
        if getArgs().set_freq:
            self.adb.setFrequency(getArgs().set_freq)

    def _setLogCatSize(self):
        repeat = True
        size = 131072
        while (repeat and size > 256):
            repeat = False
            ret = self.adb.logcat("-G", str(size) + "K")
            if ret.find("failed to") >= 0:
                repeat = True
                size = int(size / 2)

    def rebootDevice(self):
        self.adb.reboot()
        self.waitForDevice(180)

        # Need to wait a bit more after the device is rebooted
        time.sleep(20)
        # may need to set log size again after reboot
        self._setLogCatSize()
        if getArgs().set_freq:
            self.adb.setFrequency(getArgs().set_freq)

    def runCommand(self, cmd):
        return self.adb.shell(cmd)

    def runBenchmark(self, cmd, *args, **kwargs):
        if not isinstance(cmd, list):
            cmd = shlex.split(cmd)
        self.adb.logcat('-b', 'all', '-c')
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
                cmd = ["nohup"] + ["sh", "-c", "'" + " ".join(cmd) + "'"] + \
                    [">", "/dev/null", "2>&1"]
                log_to_screen_only = True
                android_kwargs["non_blocking"] = True
                del platform_args["power"]
            if "timeout" in platform_args and platform_args["timeout"]:
                android_kwargs["timeout"] = platform_args["timeout"]
                del platform_args["timeout"]
        log_screen = self.adb.shell(cmd, **android_kwargs)
        log_logcat = ""
        if not log_to_screen_only:
            log_logcat = self.adb.logcat('-d')
        return log_screen + log_logcat

    def collectMetaData(self, info):
        meta = super(AndroidPlatform, self).collectMetaData(info)
        meta['platform_hash'] = self.platform_hash
        return meta

    def copyFilesToPlatform(self, files, target_dir=None):
        target_dir = (self.adb.dir if target_dir is None else target_dir) + "/"
        if isinstance(files, string_types):
            target_file = target_dir + os.path.basename(files)
            self.adb.push(files, target_file)
            return target_file
        elif isinstance(files, list):
            target_files = []
            for f in files:
                target_files.append(self.copyFilesToPlatform(f, target_dir))
            return target_files
        elif isinstance(files, dict):
            d = {}
            for f in files:
                d[f] = self.copyFilesToPlatform(files[f], target_dir)
            return d
        else:
            assert False, "Cannot reach here"
        return None

    def moveFilesFromPlatform(self, files, target_dir):
        assert target_dir is not None, "Target directory must be specified."
        if isinstance(files, string_types):
            return self._moveOneFileFromPlatform(files, target_dir)
        elif isinstance(files, list):
            output_files = []
            for f in files:
                output_files.append(self.moveFilesFromPlatform(f, target_dir))
            return output_files
        elif isinstance(files, dict):
            output_files = {}
            for f in files:
                output_file = self.moveFilesFromPlatform(files[f],
                                                         target_dir)
                output_files[f] = output_file
            return output_files
        else:
            assert False, "Cannot reach here"
        return None

    def _moveOneFileFromPlatform(self, f, target_dir):
        basename = os.path.basename(f)
        android_file = f if f.startswith('/') else self.adb.dir + basename
        output_file = target_dir + basename
        self.adb.pull(android_file, output_file)
        self.adb.shell(["rm", "-f", android_file])
        return output_file

    def delFilesFromPlatform(self, files):
        if isinstance(files, string_types):
            self.adb.deleteFile(files)
        elif isinstance(files, list):
            for f in files:
                self.adb.deleteFile(f)
        elif isinstance(files, dict):
            for f in files:
                self.adb.deleteFile(files[f])
        else:
            assert False, "Cannot reach here"

    def getOutputDir(self):
        return self.adb.dir

    def killProgram(self, program):
        res = self.adb.shell(["ps", "|", "grep", program])
        results = res.split("\n")
        pattern = re.compile(r"^shell\s+(\d+)\s+")
        for result in results:
            match = pattern.match(result)
            if match:
                pid = match.group(1)
                self.adb.shell(["kill", pid])

    def waitForDevice(self, timeout):
        period = int(timeout / 20) + 1
        num = int(timeout / period)
        count = 0
        ls = None
        while ls is None and count < num:
            ls = self.adb.shell(['ls', self.adb.dir])
            time.sleep(period)
        if ls is None:
            getLogger().error("Cannot reach device {} ({}) after {}.".
                              format(self.platform, self.platform_hash,
                                     timeout))
