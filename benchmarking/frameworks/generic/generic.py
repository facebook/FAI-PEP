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
        # import pdb; pdb.set_trace()
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
        if model is not None and "cached_models" in model:
            cached_models = \
                platform.copyFilesToPlatform(model["cached_models"])
            commands = self._updateModelPath(model, commands)

        # todo: input files
        output = platform.runBenchmark(commands, True)

        # todo: output files
        output_files = None

        # cleanup
        if model is not None and "cached_modes" in model:
            platform.delFilesFromPlatform(cached_models)
        platform.delFilesFromPlatform(program)

        return output, output_files

    def _updateModelPath(self, model, commands):
        _args = commands.split()
        init_net = model["files"]["init"]["filename"]
        predict_net = model["files"]["predict"]["filename"]
        for i in range(len(_args)):
            if _args[i] == init_net:
                _args[i] = os.path.basename(model["cached_models"]["init"])
            elif _args[i] == predict_net:
                _args[i] = os.path.basename(model["cached_models"]["predict"])
        return ' '.join(_args)
