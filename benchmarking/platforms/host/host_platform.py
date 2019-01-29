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
from utils.subprocess_with_logger import processRun


class HostPlatform(PlatformBase):
    def __init__(self, tempdir, args):
        platform_hash = str(socket.gethostname())
        if args.platform_sig is not None:
            platform_name = str(args.platform_sig)
        else:
            platform_name = platform.platform() + "-" + \
                               self._getProcessorName()
        self.tempdir = os.path.join(tempdir, platform_hash)
        hdb = HDB(platform_hash, tempdir)
        super(HostPlatform, self).__init__(self.tempdir, self.tempdir, hdb, args)

        # reset the platform and platform hash
        self.setPlatform(platform_name)
        self.setPlatformHash(platform_hash)
        if os.path.exists(self.tempdir):
            shutil.rmtree(self.tempdir)
        os.makedirs(self.tempdir, 0o777)
        self.type = "host"

    def runBenchmark(self, cmd, *args, **kwargs):
        if not isinstance(cmd, list):
            cmd = shlex.split(cmd)
        platform_args = {}
        env = os.environ
        if "platform_args" in kwargs:
            platform_args = kwargs["platform_args"]
            if "env" in platform_args:
                customized_env = platform_args["env"]
                for k in customized_env:
                    env[k] = str(customized_env[k])
                platform_args["env"] = env

        output, _ = processRun(cmd, **platform_args)
        return output

    def _getProcessorName(self):
        if platform.system() == "Windows":
            return platform.processor()
        elif platform.system() == "Darwin":
            processor_info, _ = processRun(
                ["sysctl", "-n", "machdep.cpu.brand_string"])
            if len(processor_info) > 0:
                return processor_info[0].rstrip()
        elif platform.system() == "Linux":
            processor_info, _ = processRun(["cat", "/proc/cpuinfo"])
            if processor_info:
                for line in processor_info:
                    if "model name" in line:
                        return re.sub(".*model name.*:", "", line, 1)
        return ""

    def getOutputDir(self):
        out_dir = os.path.join(self.tempdir, "output")
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir, 0o777)
        return out_dir
