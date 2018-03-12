#!/usr/bin/env python3.6

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
import shutil
import subprocess

from platforms.platform_base import PlatformBase
from utils.custom_logger import getLogger
from utils.subprocess_with_logger import processRun


class HostPlatform(PlatformBase):
    def __init__(self, tempdir):
        super(HostPlatform, self).__init__()
        self.setPlatform(platform.platform() + "-" + self._getProcessorName())
        self.tempdir = tempdir + "/" + self.platform
        os.makedirs(self.tempdir, 0o777, True)

    def runBenchmark(self, cmd):
        getLogger().info("Running: %s", ' '.join(cmd))
        pipes = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        std_out, std_err = pipes.communicate()
        assert pipes.returncode == 0, "Benchmark run failed"
        if len(std_err):
            return std_err.decode("utf-8", "ignore")
        else:
            return ""

    def _getProcessorName(self):
        if platform.system() == "Windows":
            return platform.processor()
        elif platform.system() == "Darwin":
            return processRun(["sysctl", "-n", "machdep.cpu.brand_string"])\
                .rstrip()
        elif platform.system() == "Linux":
            proc_info = processRun(["cat", "/proc/cpuinfo"])
            for line in proc_info.split("\n"):
                if "model name" in line:
                    return re.sub(".*model name.*:", "", line, 1)
        return ""

    def copyFilesToPlatform(self, files, target_dir=None):
        if target_dir is None:
            return files
        else:
            if isinstance(files, str):
                tgt_file = target_dir + "/" + os.path.basename(files)
                shutil.copyfile(files, tgt_file)
                return target_dir + "/" + os.path.basename(files)
            elif isinstance(files, list):
                target_files = []
                for f in files:
                    target_files.append(self.copyFilesToPlatform(f,
                                                                 target_dir))
                return target_files
            elif isinstance(files, dict):
                tgt = {}
                for f in files:
                    tgt[f] = self.copyFilesToPlatform(files[f], target_dir)
                return tgt
            else:
                assert False, "Cannot reach here"

    def moveFilesFromPlatform(self, files, target_dir=None):
        if isinstance(files, str):
            tgt_file = self.copyFilesToPlatform(files, target_dir)
            if tgt_file != files:
                os.remove(files)
            return tgt_file
        elif isinstance(files, list):
            tgt_files = []
            for f in files:
                tgt_files.append(self.moveFilesFromPlatform(f, target_dir))
            return tgt_files
        elif isinstance(files, dict):
            tgt = {}
            for f in files:
                tgt[f] = self.moveFilesFromPlatform(files[f], target_dir)
            return tgt
        else:
            assert False, "Cannot reach here"

    def delFilesFromPlatform(self, files):
        pass

    def getOutputDir(self):
        out_dir = self.tempdir + "/output/"
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir, 0o777, True)
        return out_dir
