#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import re
from six import string_types

from platforms.platform_util_base import PlatformUtilBase
from utils.custom_logger import getLogger


class ADB(PlatformUtilBase):
    def __init__(self, device=None, tempdir=None):
        super(ADB, self).__init__(device, tempdir)

    def run(self, *args, **kwargs):
        adb = self._addADB()
        return super(ADB, self).run(adb, *args, **kwargs)

    def runAsync(self, *args, **kwargs):
        adb = self._addADB()
        return super(ADB, self).runAsync(adb, *args, **kwargs)

    def push(self, src, tgt):
        # Always remove the old file before pushing the new file
        self.deleteFile(tgt)
        return self.run("push", src, tgt)

    def pull(self, src, tgt):
        return self.run("pull", src, tgt)

    def logcat(self, *args):
        return self.run("logcat", *args)

    def reboot(self):
        return self.run("reboot")

    def deleteFile(self, file):
        return self.shell(['rm', '-f', file])

    def shell(self, cmd, **kwargs):
        dft = None
        if 'default' in kwargs:
            dft = kwargs.pop('default')
        val = self.run("shell", cmd, **kwargs)
        if val is None and dft is not None:
            val = dft
        return val

    def su_shell(self, cmd, **kwargs):
        su_cmd = ["su", "-c"]
        su_cmd.extend(cmd)
        return self.shell(su_cmd, **kwargs)

    def setFrequency(self, target):
        ret = self.shell(["su", "-v", "2>&1"])
        if ret.find("not found") >= 0:
            getLogger().info("Device {} is not rooted.".format(self.device))
            return

        cpus = self._getCPUs()
        for cpu in cpus:
            freq_target = None
            if isinstance(target, dict):
                if cpu in target:
                    freq_target = target[cpu]
                else:
                    freq_target = "mid"
            elif isinstance(target, string_types):
                freq_target = target
            else:
                assert False, "Unsupported frequency target"
            self._setOneCPUFrequency(cpu, freq_target)

    def _addADB(self):
        adb = ["adb"]
        if self.device:
            adb.extend(["-s", self.device])
        return adb

    def _setOneCPUFrequency(self, cpu, freq_target):
        directory = "/sys/devices/system/cpu/" + cpu + "/"

        scaling_governor = directory + "cpufreq/scaling_governor"
        self.su_shell(["\"echo userspace > {}\"".format(scaling_governor)])
        set_scaling_governor = self.su_shell(["cat", scaling_governor]).strip()
        assert set_scaling_governor == "userspace", \
            getLogger().fatal("Cannot set scaling governor to userspace")

        avail_freq = directory + "cpufreq/scaling_available_frequencies"
        freqs = self.su_shell(["cat", avail_freq]).strip().split(" ")
        assert len(freqs) > 0, "No available frequencies"
        freq = None
        if freq_target == "max":
            freq = freqs[-1]
        elif freq_target == "min":
            freq = freqs[0]
        elif freq_target == "mid":
            freq = freqs[int(len(freqs) / 2)]
        else:
            assert re.match("^\d+$", freq_target), \
                "Frequency target is not integer"
            freq = freq_target
        minfreq = directory + "cpufreq/scaling_min_freq"
        self.su_shell(["\"echo {} > {}\"".format(freq, minfreq)])
        maxfreq = directory + "cpufreq/scaling_max_freq"
        self.su_shell(["\"echo {} > {}\"".format(freq, maxfreq)])
        curr_speed = directory + "cpufreq/scaling_cur_freq"
        set_freq = self.su_shell(["cat", curr_speed]).strip()
        assert set_freq == freq, \
            "Unable to set frequency {} for {}".format(freq_target, cpu)
        getLogger().info("On {}, set {} frequency to {}".
                         format(self.device, cpu, freq))

    def _getCPUs(self):
        dirs = self.su_shell(["ls", "/sys/devices/system/cpu/"])
        dirs = dirs.split("\n")
        return [x for x in dirs if re.match("^cpu\d+$", x)]
