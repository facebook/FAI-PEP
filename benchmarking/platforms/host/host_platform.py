#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import platform
import os
import re
import shlex
import shutil
import socket

from platforms.host.hdb import HDB
from platforms.platform_base import PlatformBase
from utils.arg_parse import getArgs
from utils.subprocess_with_logger import processRun


class HostPlatform(PlatformBase):
    def __init__(self, tempdir):
        platform_hash = str(socket.gethostname())
        if getArgs().platform_sig is not None:
            platform = str(getArgs().platform_sig)
        else:
            platform = platform.platform() + "-" + \
                               self._getProcessorName()
        self.tempdir = os.path.join(tempdir, platform + '_' +
                                    platform_hash)
        hdb = HDB(platform_hash)
        super(HostPlatform, self).__init__(self.tempdir, self.tempdir, hdb)

        # reset the platform and platform hash
        self.setPlatform(platform)
        self.setPlatformHash(platform_hash)
        if os.path.exists(self.tempdir):
            shutil.rmtree(self.tempdir)
        os.makedirs(self.tempdir, 0o777)
        self.type = "host"

    def runBenchmark(self, cmd, *args, **kwargs):
        if not isinstance(cmd, list):
            cmd = shlex.split(cmd)
        host_kwargs = {}
        if "platform_args" in kwargs and "timeout" in kwargs["platform_args"]:
            host_kwargs["timeout"] = kwargs["platform_args"]["timeout"]
        output, _ = processRun(cmd, **host_kwargs)
        return output

    def _getProcessorName(self):
        if platform.system() == "Windows":
            return platform.processor()
        elif platform.system() == "Darwin":
            processor_info, _ = processRun(
                ["sysctl", "-n", "machdep.cpu.brand_string"])
            if processor_info:
                return processor_info.rstrip()
        elif platform.system() == "Linux":
            processor_info, _ = processRun(["cat", "/proc/cpuinfo"])
            if processor_info:
                for line in processor_info.split("\n"):
                    if "model name" in line:
                        return re.sub(".*model name.*:", "", line, 1)
        return ""

    def getOutputDir(self):
        out_dir = os.path.join(self.tempdir, "output")
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir, 0o777)
        return out_dir
