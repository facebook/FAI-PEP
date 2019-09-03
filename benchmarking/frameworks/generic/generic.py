#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import os
from frameworks.framework_base import FrameworkBase


class GenericFramework(FrameworkBase):
    def __init__(self, tempdir, args):
        self.tempdir = os.path.join(tempdir, self.getName())
        os.makedirs(self.tempdir, 0o777)

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

        program = platform.copyFilesToPlatform(info["programs"]["program"]["location"])

        commands = test["commands"]
        model_files = None
        if model is not None and "files" in model:
            model_files = {name: model["files"][name]["location"]
                           for name in model["files"]}
            model_files = \
                platform.copyFilesToPlatform(model_files)

        libraries = []
        if "libraries" in model:
            for entry in model["libraries"]:
                target = entry["target"] \
                    if "target" in entry else platform.adb.dir
            libraries.append(platform.copyFilesToPlatform(
                entry["location"], target))

        # run benchmark
        output, meta = platform.runBenchmark(commands, log_to_screen_only=True)

        # todo: output files
        output_files = None

        # cleanup
        if model_files:
            platform.delFilesFromPlatform(model_files)
        platform.delFilesFromPlatform(program)

        return output, output_files

    def verifyBenchmarkFile(self, benchmark, filename, is_post):
        pass
