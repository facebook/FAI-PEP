#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import collections
import os
import re
import shutil
from frameworks.framework_base import FrameworkBase
from utils.custom_logger import getLogger


class GenericFramework(FrameworkBase):
    def __init__(self, tempdir):
        self.tempdir = tempdir + "/" + self.getName()
        os.makedirs(self.tempdir, 0o777, True)

    def getName(self):
        return "generic"

    def runBenchmark(self, info, benchmark, platform):
        tests = benchmark["tests"]
        assert len(tests) == 1, "At this point, only one test should " + \
            "exist in one benchmark. However, benchmark " + \
            "{} doesn't.".format(benchmark["name"])
        test = tests[0]

        model = None
        if "model" in benchmark:
            model = benchmark["model"]

        program = platform.copyFilesToPlatform(info["program"])

        commands = test["commands"]
        model_files = None
        if model is not None and "files" in model:
            model_files = {name: model["files"][name]["location"]
                           for name in model["files"]}
            model_files = \
                platform.copyFilesToPlatform(model_files)

        # todo: input files

        # run benchmark
        output = platform.runBenchmark(commands, True)

        # todo: output files
        output_files = None

        # cleanup
        if model_files:
            platform.delFilesFromPlatform(model_files)
        platform.delFilesFromPlatform(program)

        return output, output_files

    def verifyBenchmarkFile(self, benchmark, filename, is_post):
        pass
