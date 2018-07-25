#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import abc
import os
import shutil
import time


class FrameworkBase(object):
    def __init__(self):
        pass

    @abc.abstractmethod
    def getName(self):
        return "Error"

    @abc.abstractmethod
    def runBenchmark(self, info, benchmark, platform):
        model = benchmark["model"]
        tests = benchmark["tests"]
        assert len(tests) == 1, "At this point, only one test should " + \
            "exist in one benchmark. However, benchmark " + \
            "{} doesn't.".format(benchmark["name"])
        test = tests[0]
        program = platform.copyFilesToPlatform(info["program"])
        shared_libs = None
        if "shared_libs" in info:
            shared_libs = platform.copyFilesToPlatform(info["shared_libs"])

        model_files = {name: model["files"][name]["location"]
                       for name in model["files"]}
        model_files = platform.copyFilesToPlatform(model_files)
        input_files = None
        if "input_files" in test:
            input_files = {name: test["input_files"][name]["location"]
                           for name in test["input_files"]}
            input_files = platform.copyFilesToPlatform(input_files)

        cmd = self.composeRunCommand(platform, program, test, model_files,
                                     input_files, shared_libs)
        total_num = test["iter"]

        platform_args = model["platform_args"] if "platform_args" in model \
            else {}

        if test["metric"] == "power":
            platform_args["power"] = True
            # in power metric, the output is ignored
            total_num = 0
            platform.killProgram(program)

        output = self.runOnPlatform(total_num, cmd, platform, platform_args)
        output_files = None
        if "output_files" in test:
            files = {}
            for of in test["output_files"]:
                files[of] = platform.getOutputDir() + "/" + of + ".txt"
            target_dir = self.tempdir + "/output/"
            shutil.rmtree(target_dir, True)
            os.makedirs(target_dir)
            output_files = \
                platform.moveFilesFromPlatform(files, target_dir)

        if test["metric"] == "power":
            collection_time = test["collection_time"]
            from utils.monsoon_power import collectPowerData
            output = collectPowerData(collection_time, test["iter"])
            platform.waitForDevice(20)
            # kill the process if exists
            platform.killProgram(program)

        if len(output) > 0:
            platform.delFilesFromPlatform(model_files)
            platform.delFilesFromPlatform(program)
            if shared_libs is not None:
                platform.delFilesFromPlatform(shared_libs)
            if input_files is not None:
                platform.delFilesFromPlatform(input_files)
        return output, output_files

    @abc.abstractmethod
    def composeRunCommand(self, platform, program, test, model_files,
                          input_files, shared_libs):
        assert False, "Child class need to implement composeRunCommand"

    @abc.abstractmethod
    def runOnPlatform(self, total_num, cmd, platform, platform_args):
        assert False, "Child class need to implement runOnPlatform"

    @abc.abstractmethod
    def verifyBenchmarkFile(self, benchmark, filename, is_post):
        return None

    def rewriteBenchmarkTests(self, benchmark, filename):
        pass
