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
import sys

from data_converters.data_converters import getConverters
from utils.custom_logger import getLogger
from utils.subprocess_with_logger import processRun
from utils.utilities import deepMerge, deepReplace


class FrameworkBase(object):
    def __init__(self):
        self.converters = getConverters()
        self.tmpdir = None
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
        hostdir = self._createHostDir()
        deepReplace(test, "{TGTDIR}", platform.getOutputDir())
        deepReplace(test, "{HOSTDIR}", hostdir)

        program_files = {name: info["programs"][name]["location"]
                         for name in info["programs"]}
        tgt_program_files, host_program_files = \
            self._separatePrograms(program_files, test["commands"])
        platform.preprocess(programs=program_files)
        model_files = {name: model["files"][name]["location"]
                       for name in model["files"]}

        programs = platform.copyFilesToPlatform(tgt_program_files)
        deepMerge(programs, host_program_files)

        input_files = None
        if "input_files" in test:
            input_files = {name: test["input_files"][name]["location"]
                           for name in test["input_files"]}

        test_files = {}
        if "files" in test:
            test_files = {name: test["files"][name]["location"]
                          for name in test["files"]}
        # Let's handle preprocess comamnd first,
        # since we will copy all files into host
        if "preprocess" in test:
            # simple thing first, let's assume preprocess is self contained
            # check the program to executable
            if "files" in test["preprocess"] and \
                    "program" in test["preprocess"]["files"]:
                host_program_path = \
                    test["preprocess"]["files"]["program"]["location"]
                os.chmod(host_program_path, 0o777)

            # will deprecate in the future
            if "files" in test["preprocess"]:
                preprocess_files = \
                    {name: test["preprocess"]["files"][name]["location"]
                     for name in test["preprocess"]["files"]}
                deepMerge(test_files, preprocess_files)

            if "commands" in test["preprocess"]:
                commands = test["preprocess"]["commands"]
            elif "command" in test["preprocess"]:
                commands = [test["preprocess"]["command"]]
            preprocess_cmds = self.composeRunCommand(commands, platform,
                                                     programs, model,
                                                     test, model_files,
                                                     input_files, None,
                                                     None, None)
            # run the preprocess command on host machines
            for cmd in preprocess_cmds:
                getLogger().info("Running on Host: %s", cmd)
                run_result, _ = processRun([cmd], shell=True)
                if run_result:
                    getLogger().info("Preprocessing output: %s", run_result)

        if input_files:
            tgt_input_files = platform.copyFilesToPlatform(input_files)
        shared_libs = None
        if "shared_libs" in info:
            shared_libs = platform.copyFilesToPlatform(info["shared_libs"])

        tgt_model_files = platform.copyFilesToPlatform(model_files)

        tgt_result_files = None
        if "output_files" in test:
            tgt_result_files = {}
            for of in test["output_files"]:
                tgt_result_files[of] = \
                    {name: test["output_files"][name]["location"]
                     for name in test["output_files"]}
        cmds = self.composeRunCommand(test["commands"], platform,
                                      programs, model, test,
                                      tgt_model_files,
                                      tgt_input_files, tgt_result_files,
                                      shared_libs, preprocess_files)
        total_num = test["iter"]

        if "platform_args" in test:
            platform_args = test["platform_args"]
        elif "platform_args" in model:
            platform_args = model["platform_args"]
        else:
            platform_args = {}

        if sys.version_info > (3, 0):
            if 'timeout' in model:
                platform_args['timeout'] = model['timeout']
            if 'timeout' in test:
                platform_args['timeout'] = test['timeout']

        program = programs["program"] if "program" in programs else ""
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
        output = self.runOnPlatform(total_num, cmds, platform, platform_args,
                                    converter)
        output_files = None
        if "output_files" in test:
            target_dir = os.path.join(self.tempdir, "output")
            shutil.rmtree(target_dir, True)
            os.makedirs(target_dir)
            output_files = \
                platform.moveFilesFromPlatform(tgt_result_files, target_dir)

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
            platform.delFilesFromPlatform(tgt_model_files)
            platform.delFilesFromPlatform(program)
            if shared_libs is not None:
                platform.delFilesFromPlatform(shared_libs)
            if input_files is not None:
                platform.delFilesFromPlatform(input_files)

        if "postprocess" in test:
            if "files" in test["postprocess"] and \
                    "program" in test["preprocess"]["files"]:
                host_program_path = \
                    test["postprocess"]["files"]["program"]["location"]
                os.chmod(host_program_path, 0o777)

            postprocess_cmd = self.composeProcessCommand(
                test["postprocess"], model, test, programs, model_files)
            # run the preprocess command on host machines
            getLogger().info(
                "Running on Host for post-processing: %s", postprocess_cmd)
            run_result, _ = processRun([postprocess_cmd], shell=True)
            if run_result:
                getLogger().info("Postprocessing output: %s", run_result)
        return output, output_files

    def composeProcessCommand(self, process_info, model, test,
                              programs, model_files):
        files_db = {}
        if "files" in process_info:
            for f_key in process_info["files"]:
                f_value = process_info["files"][f_key]
                files_db[f_key] = f_value["location"]
        return self._getReplacedCommand(process_info["command"],
                                        files_db,
                                        model, test, programs, model_files)

    @abc.abstractmethod
    def composeRunCommand(self, commands, platform,
                          programs, model, test, model_files,
                          input_files, output_files, shared_libs,
                          preprocess_files=None):
        if commands is None or not isinstance(commands, list):
            return None
        files = input_files.copy() if input_files is not None else {}
        files.update(output_files if output_files is not None else {})
        files.update(preprocess_files if preprocess_files is not None else {})
        extra_arguments = " " + model["command_args"] \
            if "command_args" in model else ""
        composed_commands = []
        for command in commands:
            more_args = extra_arguments if "{program}" in command else ""
            command = self._getReplacedCommand(command, files, model, test,
                                               programs, model_files)
            command += more_args
            composed_commands.append(command)
        return composed_commands

    def _getReplacedCommand(self, command, files, model, test,
                            programs, model_files):
        pattern = re.compile("\{([\w|\.]+)\}")
        prev_count = 1000000
        while True:
            results = []
            for m in pattern.finditer(command):
                results.append({
                    "start": m.start(),
                    "end": m.end(),
                    "content": m.group(1)
                })
            if len(results) == prev_count:
                break
            prev_count = len(results)
            results.reverse()
            for res in results:
                replace = self._getMatchedString(test, res["content"], files)
                if replace is None:
                    # TODO: handle shared libraries
                    replace = self._getMatchedString(model, res["content"],
                                                     model_files)
                if replace is None:
                    replace = self._getMatchedString(programs, res["content"])

                if replace:
                    command = command[:res["start"]] + "'" + replace + "'" + \
                        command[res["end"]:]
        return command

    def _getMatchedString(self, root, match, files=None):
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

    def _separatePrograms(self, program_files, commands):
        tgt_program_files = {}
        for command in commands:
            for name in program_files:
                if "{"+name+"}" in command:
                    tgt_program_files[name] = program_files[name]
        host_program_files = {name : program_files[name]
                              for name in program_files
                              if name not in tgt_program_files}
        return tgt_program_files, host_program_files

    def _createHostDir(self):
        hostdir = os.path.join(self.tempdir, "host")
        i = 0
        while os.path.exists(hostdir):
            hostdir = os.path.join(self.tempdir, "host" + str(i))
            i = i + 1
        os.makedirs(hostdir, 0o777)
        return hostdir
