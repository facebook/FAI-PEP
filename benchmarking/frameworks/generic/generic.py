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
        model = None
        if "model" in benchmark:
            model = benchmark["model"]
        commands = benchmark["tests"][0]["commands"]
        program = platform.copyFilesToPlatform(info["program"])

        shared_libs = None
        if "shared_libs" in info:
            shared_libs = platform.copyFilesToPlatform(info["shared_libs"])

        if model is not None and "cached_modes" in model:
            cached_models = \
                platform.copyFilesToPlatform(model["cached_models"])

        # todo: input files

        output = platform.runBenchmark(commands, True)

        # todo: output files
        output_files = None

        # cleanup
        if model is not None and "cached_modes" in model:
            platform.delFilesFromPlatform(cached_models)
        platform.delFilesFromPlatform(program)
        if shared_libs is not None:
            platform.delFilesFromPlatform(shared_libs)

        return output, output_files
