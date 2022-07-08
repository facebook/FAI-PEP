#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import re

from platforms.platform_util_base import PlatformUtilBase
from six import string_types
from utils.custom_logger import getLogger


class ADB(PlatformUtilBase):
    def __init__(self, device=None, tempdir=None):
        super(ADB, self).__init__(device, tempdir)

    def run(self, *args, **kwargs):
        adb = self._addADB()
        return super(ADB, self).run(adb, *args, **kwargs)

    def push(self, src, tgt):
        # Always remove the old file before pushing the new file
        self.deleteFile(tgt)
        return self.run("push", src, tgt)

    def pull(self, src, tgt):
        return self.run("pull", src, tgt)

    def logcat(self, *args, timeout=30, retry=1):
        # logcat can hang if a device becomes unavailable
        return self.run("logcat", *args, timeout=timeout, retry=retry)

    def reboot(self):
        try:
            self.run("reboot")
            return True
        except Exception:
            getLogger().critical(
                f"Rebooting failure for device {self.device}.",
                exc_info=True,
            )
            return False

    def root(self, silent=False):
        return self.restart_adbd(root=True, silent=silent)

    def unroot(self, silent=False):
        return self.restart_adbd(root=False, silent=silent)

    def user_is_root(self):
        return self.get_user() == "root"

    def get_user(self):
        try:
            return self.shell("whoami", retry=1, silent=True)[0]
        except Exception:
            getLogger().exception("whoami failed.")
            return None  # could fail on unrooted device

    def restart_adbd(self, root=False, silent=False):
        user = self.get_user()
        if user is not None:
            try:
                if root and user != "root":
                    if not silent:
                        getLogger().info("Restarting adbd with root privilege.")
                    self.run(["root"], retry=1, silent=True)
                elif not root and user == "root":
                    if not silent:
                        getLogger().info("Restarting adbd with nonroot privilege.")
                    self.run(["unroot"], retry=1, silent=True)
                else:
                    return True  # no-op

                # Check if change worked
                user = self.get_user()
                if not silent:
                    getLogger().info(f"adbd user is now: {user}.")
                return user == "root" if root else user != "root"
            except Exception:
                err_text = f"Error while restarting adbd with {'non' if not root else ''}root privilege."
                if silent:
                    # still log error but no alert if in silent mode
                    getLogger().error(err_text, exc_info=True)

                else:
                    getLogger().critical(err_text, exc_info=True)
        return False

    def deleteFile(self, file, **kwargs):
        return self.shell(["rm", "-rf", file], **kwargs)

    def shell(self, cmd, **kwargs):
        dft = None
        if "default" in kwargs:
            dft = kwargs.pop("default")
        val = self.run("shell", cmd, **kwargs)
        if val is None and dft is not None:
            val = dft
        return val

    def su_shell(self, cmd, **kwargs):
        su_cmd = ["su", "-c"]
        su_cmd.extend(cmd)
        return self.shell(su_cmd, **kwargs)

    def getprop(self, property: str, **kwargs) -> str:
        if "default" not in kwargs:
            kwargs["default"] = [""]
        result = self.run(["shell", "getprop", property], **kwargs)
        if type(result) is not list:
            getLogger().error(
                f"adb.getprop(\"{property}\") unexpectedly returned {type(result)} '{result}'."
            )
            return ""
        if len(result) == 0:
            getLogger().error(f'adb.getprop("{property}") returned an empty list.')
            return ""

        retval = result[0].strip()
        getLogger().info(f"adb.getprop(\"{property}\") returned '{retval}'.")
        return retval

    def setprop(self, property, value, **kwargs):
        self.shell(["setprop", property, value], **kwargs)

    def getBatteryProp(self, property: str, silent=True) -> str:
        """
        For rooted devices, you should already establish "user is root" before calling
        """
        if self.user_is_root():
            path = "/sys/class/power_supply/battery/" + property
            # Make sure path exists before trying to get it
            if not (
                self.shell(["[", "-f", '"' + path + '"', "]"], retry=1, silent=silent)
            ):
                return self.shell(
                    ["cat", path],
                    retry=1,
                    silent=silent,
                )[0]

        return ""

    def isRootedDevice(self, silent=True) -> bool:
        try:
            ret = self.shell(
                ["id", "-u", "2>&1"], retry=1, silent=silent, ignore_status=silent
            )
            if not silent:
                getLogger().info(f"id -u returned '{ret}'.")
            if "0" in ret:
                return True

            ret = self.shell(
                ["which", "su", "2>&1"], retry=1, silent=silent, ignore_status=silent
            )
            if not silent:
                getLogger().info(f"which su returned '{ret}'.")

            is_rooted = (
                ret is not None and len(ret) > 0 and ret[0].find("not found") == -1
            )
            return is_rooted

        except Exception:
            return False

    def setFrequency(self, target):
        if not self.isRootedDevice():
            getLogger().warning(
                f"Cannot set frequency on unrooted device {self.device}."
            )
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
                raise AssertionError("Unsupported frequency target")
            self._setOneCPUFrequency(cpu, freq_target)

    def _addADB(self):
        adb = ["adb"]
        if self.device:
            adb.extend(["-s", self.device])
        return adb

    def _setOneCPUFrequency(self, cpu, freq_target):
        directory = os.path.join(*["/sys/devices/system/cpu/", cpu, "/"])

        scaling_governor = directory + "cpufreq/scaling_governor"
        self.su_shell(['"echo userspace > {}"'.format(scaling_governor)])
        set_scaling_governor = self.su_shell(["cat", scaling_governor]).strip()
        assert set_scaling_governor == "userspace", getLogger().fatal(
            "Cannot set scaling governor to userspace"
        )

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
            assert re.match(r"^\d+$", freq_target), "Frequency target is not integer"
            freq = freq_target
        minfreq = directory + "cpufreq/scaling_min_freq"
        self.su_shell(['"echo {} > {}"'.format(freq, minfreq)])
        maxfreq = directory + "cpufreq/scaling_max_freq"
        self.su_shell(['"echo {} > {}"'.format(freq, maxfreq)])
        curr_speed = directory + "cpufreq/scaling_cur_freq"
        set_freq = self.su_shell(["cat", curr_speed]).strip()
        assert set_freq == freq, "Unable to set frequency {} for {}".format(
            freq_target, cpu
        )
        getLogger().info("On {}, set {} frequency to {}".format(self.device, cpu, freq))

    def _getCPUs(self):
        dirs = self.su_shell(["ls", "/sys/devices/system/cpu/"])
        dirs = dirs.split("\n")
        return [x for x in dirs if re.match(r"^cpu\d+$", x)]
