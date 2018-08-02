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
import re
import shutil
from six import string_types

from data_converters.data_converters import getConverters
from utils.custom_logger import getLogger


class FrameworkBase(object):
    def __init__(self):
        self.converters = getConverters()
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
        result_files = None
        if "output_files" in test:
            result_files = {}
            for of in test["output_files"]:
                result_files[of] = platform.getOutputDir() + "/" + of + ".txt"

        cmd = self.composeRunCommand(platform, program, model, test,
                                     model_files, input_files, result_files,
                                     shared_libs)
        total_num = test["iter"]

        if "platform_args" in test:
            platform_args = test["platform_args"]
        elif "platform_args" in model:
            platform_args = model["platform_args"]
        else:
            platform_args = {}

        if test["metric"] == "power":
            platform_args["power"] = True
            # in power metric, the output is ignored
            total_num = 0
            platform.killProgram(program)

        if "converter" in model:
            converter_name = model["converter"]
            assert converter_name in self.converters, \
                "Unknown converter {}".format(converter_name)
            converter = self.converters[converter_name]
        else:
            converter = None
        output = self.runOnPlatform(total_num, cmd, platform, platform_args,
                                    converter)
        output_files = None
        if "output_files" in test:
            target_dir = self.tempdir + "/output/"
            shutil.rmtree(target_dir, True)
            os.makedirs(target_dir)
            output_files = \
                platform.moveFilesFromPlatform(result_files, target_dir)

        if test["metric"] == "power":
            collection_time = test["collection_time"] \
                if "collection_time" in test else 180
            voltage = float(test["voltage"]) if "voltage" in test else 4.0
            from utils.monsoon_power import collectPowerData
            output = collectPowerData(collection_time, voltage, test["iter"])
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
    def composeRunCommand(self, platform, program, model, test, model_files,
                          input_files, output_files, shared_libs):
        if "arguments" not in test:
            return None
        arguments = test["arguments"]
        command = arguments
        pattern = re.compile("\{([\w|\.]+)\}")
        results = []
        for m in pattern.finditer(arguments):
            results.append({
                "start": m.start(),
                "end": m.end(),
                "content": m.group(1)
            })
        results.reverse()
        files = input_files.copy() if input_files is not None else {}
        files.update(output_files if output_files is not None else {})
        for res in results:
            replace = self._getMatchedString(test, res["content"], files)
            if replace is None:
                # TODO: handle shared libraries
                replace = self._getMatchedString(model, res["content"],
                                                 model_files)
            if replace:
                command = command[:res["start"]] + "'" + replace + "'" + \
                    command[res["end"]:]
        command = program + " " + command
        return command

    def _getMatchedString(self, root, match, files):
        assert isinstance(root, dict), "Root must be a dictionary"
        if match in root:
            return str(root[match])
        # split on .
        fields = match.split('.')
        found = True
        entry = root
        for i in range(len(fields)):
            field = fields[i]
            if field not in entry:
                found = False
                break
            entry = entry[field]
        if not found:
            return None
        if "location" in entry:
            # is a file field
            if files and fields[-1] in files:
                return str(files[fields[-1]])
        assert isinstance(entry, string_types), "Output {}".format(entry) + \
            " is not string type"
        return str(entry)

    @abc.abstractmethod
    def runOnPlatform(self, total_num, cmd, platform, platform_args,
                      converter):
        assert False, "Child class need to implement runOnPlatform"

    @abc.abstractmethod
    def verifyBenchmarkFile(self, benchmark, filename, is_post):
        return None

    def rewriteBenchmarkTests(self, benchmark, filename):
        pass
