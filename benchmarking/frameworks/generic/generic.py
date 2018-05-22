#!/usr/bin/env python3

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
        if model is not None and "cached_files" in model:
            cached_files = \
                platform.copyFilesToPlatform(model["cached_files"])
            commands = self._updateModelPath(model, commands)

        # todo: input files

        # run benchmark
        output = platform.runBenchmark(commands, True)

        # todo: output files
        output_files = None

        # cleanup
        if model is not None and "cached_modes" in model:
            platform.delFilesFromPlatform(cached_files)
        platform.delFilesFromPlatform(program)

        return output, output_files

    def verifyBenchmarkFile(self, benchmark, filename, is_post):
        pass

    def _updateModelPath(self, model, commands):
        _args = commands.split()
        # net_names = {filename: net_type}
        net_names = {model["files"][key]["filename"]: key for key in model["files"].keys()}

        for i in range(len(_args)):
            if _args[i] in net_names:
                _args[i] = os.path.basename(model["cached_files"][net_names[_args[i]]])
        return ' '.join(_args)
