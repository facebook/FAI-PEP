#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import os
import platform
import re
import shutil
import subprocess

from platforms.platform_base import PlatformBase
from utils.arg_parse import getArgs, getParser
from utils.custom_logger import getLogger
from utils.subprocess_with_logger import processRun

getParser().add_argument("--host", action="store_true",
    help="Run the benchmark on the host.")

class HostPlatform(PlatformBase):
    def __init__(self):
        super(HostPlatform, self).__init__()
        self.setPlatform(platform.platform() + "-" + self._getProcessorName())

    def runBenchmark(self, info):
        cmd = [
            "--logtostderr", "1",
            "--init_net", getArgs().init_net,
            "--net", getArgs().net,
            "--input", getArgs().input,
            "--warmup", str(getArgs().warmup),
            "--iter", str(getArgs().iter),
            ]
        program = info['program']
        cmd.insert(0, program)
        if getArgs().input_file:
            cmd.extend(["--input_file", getArgs().input_file])
        if getArgs().input_dims:
            cmd.extend(["--input_dims", getArgs().input_dims])
        if getArgs().output:
            cmd.extend(["--output", getArgs().output])
            cmd.extend(["--output_folder", self.output_dir])
            shutil.rmtree(self.output_dir, True)
            os.makedirs(self.output_dir)
            cmd.extend(["--text_output", "true"])
        if getArgs().run_individual:
            cmd.extend(["--run_individual", "true"])
        command = ' '.join(cmd)
        getLogger().info("Running: %s", command)
        pipes = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        std_out, std_err = pipes.communicate()
        assert pipes.returncode == 0, "Benchmark run failed"
        if len(std_err):
            return std_err.decode("utf-8")
        else:
            return ""

    def collectMetaData(self, info):
        meta = super(HostPlatform, self).collectMetaData(info)
        meta[self.PLATFORM] = self.platform
        return meta

    def _getProcessorName(self):
        if platform.system() == "Windows":
            return platform.processor()
        elif platform.system() == "Darwin":
            return processRun(["sysctl", "-n", "machdep.cpu.brand_string"])
        elif platform.system() == "Linux":
            proc_info = processRun(["cat", "/proc/cpuinfo"])
            for line in proc_info.split("\n"):
                if "model name" in line:
                    return re.sub( ".*model name.*:", "", line,1)
        return ""
