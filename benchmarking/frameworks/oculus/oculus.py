#!/usr/bin/env python3

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import os
import shutil
from frameworks.framework_base import FrameworkBase


class OculusFramework(FrameworkBase):
    def __init__(self, tempdir):
        self.tempdir = tempdir + "/" + self.getName()
        os.makedirs(self.tempdir, 0o777, True)

    def getName(self):
        return "oculus"

    def runBenchmark(self, info, benchmark, platform):
        tests = benchmark["tests"]
        assert len(tests) == 1, "At this point, only one test should " + \
            "exist in one benchmark. However, benchmark " + \
            "{} doesn't.".format(benchmark["name"])

        test = tests[0]
        assert set({"model", "input", "output"}).issubset(test.keys())

        program = platform.copyFilesToPlatform(info["program"])
        commands = self._composeRunCommand(program, test)
        output = platform.runBenchmark(commands, True)

        target_dir = self.tempdir + "/output/"
        shutil.rmtree(target_dir, True)
        os.makedirs(target_dir)

        # output files are removed after being copied back
        output_files = platform.moveFilesFromPlatform(test["output"], target_dir)

        # cleanup
        # platform.delFilesFromPlatform(program)
        # for input in test["input"]:
        #     platform.delFilesFromPlatform(input)

        return output, output_files

    def _composeRunCommand(self, program, test):
        cmd = [program,
               "--model", test["model"],
               "--input", ' ' .join(test["input"]),
               "--output", ' '.join(test["output"])]
        if "batch" in test:
            cmd.append("--batch")
            cmd.append(str(test["batch"]))
        if "debug" in test:
            cmd.append("--debug")
            cmd.append(str(test["debug"]))
        if "benchmark" in test:
            cmd.append("--benchmark")
            cmd.append(str(test["benchmark"]))
        return ' '.join(cmd)
