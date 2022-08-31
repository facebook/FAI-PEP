#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import abc
import ast
import json
import os
import random
import re
import shutil
from copy import deepcopy

from bridge.file_storage.upload_files.file_uploader import FileUploader
from data_converters.data_converters import getConverters
from platforms.platforms import getHostPlatform
from profilers.perfetto.perfetto import PerfettoAnySupported
from six import string_types
from utils import software_power
from utils.custom_logger import getLogger
from utils.utilities import (
    deepMerge,
    deepReplace,
    getFAIPEPROOT,
    getModelName,
    getString,
)


class FrameworkBase(object):
    def __init__(self, args):
        self.converters = getConverters()
        self.tmpdir = None
        self.host_platform = None
        self.args = args

    @abc.abstractmethod
    def getName(self):
        return "Error"

    @abc.abstractmethod
    def runBenchmark(self, info, benchmark, platform):
        model = benchmark["model"]
        tests = benchmark["tests"]
        assert len(tests) == 1, (
            "At this point, only one test should "
            + "exist in one benchmark. However, benchmark "
            + "{} doesn't.".format(benchmark["name"])
        )
        test = tests[0]
        index = test["INDEX"] if "INDEX" in test else 0
        first_iteration = index == 0
        last_iteration = ("repeat" not in model) or (
            "repeat" in model and index == model["repeat"] - 1
        )

        if self.host_platform is None:
            self.host_platform = getHostPlatform(self.tempdir, self.args)

        program_files = {
            name: info["programs"][name]["location"] for name in info["programs"]
        }
        program_path = (
            os.path.dirname(program_files["program"])
            if "program" in program_files
            else None
        )
        stringmap_from_info = info["string_map"] if "string_map" in info else None
        self._replaceStringMap(benchmark, platform, program_path, stringmap_from_info)

        # better to be before target program files separation.
        # this way, in ios, the platform may not be copied to the target.
        platform.preprocess(programs=program_files, benchmark=benchmark)

        tgt_program_files, host_program_files = self._separatePrograms(
            program_files, test.get("commands")
        )

        tgt_program_files = platform.copyFilesToPlatform(
            tgt_program_files, copy_files=first_iteration
        )
        programs = {}
        deepMerge(programs, host_program_files)
        deepMerge(programs, tgt_program_files)

        model_files = {
            name: model["files"][name]["location"] for name in model["files"]
        }

        if "converter" in model:
            converter = model["converter"]
            assert "name" in converter, "converter field must have a name"
            assert converter["name"] in self.converters, "Unknown converter {}".format(
                converter
            )
        else:
            converter = None

        output = {}

        # inject default parameters into test
        if "iter" not in test:
            test["iter"] = -1

        # overall preprocess
        if "preprocess" in model and first_iteration:
            commands = model["preprocess"]["commands"]
            self._runCommands(
                output,
                commands,
                self.host_platform,
                programs,
                model,
                None,
                model_files,
                None,
                None,
                None,
                None,
                -1,
                converter,
            )

        input_files = (
            {
                name: test["input_files"][name]["location"]
                for name in test["input_files"]
            }
            if "input_files" in test
            else None
        )

        test_files = (
            {name: test["files"][name]["location"] for name in test["files"]}
            if "files" in test
            else {}
        )

        # Let's handle preprocess comamnd first,
        # since we will copy all files into host
        if "preprocess" in test:
            # simple thing first, let's assume preprocess is self contained
            # check the program to executable
            if (
                "files" in test["preprocess"]
                and "program" in test["preprocess"]["files"]
            ):
                host_program_path = test["preprocess"]["files"]["program"]["location"]
                os.chmod(host_program_path, 0o777)

            # will deprecate in the future
            if "files" in test["preprocess"]:
                preprocess_files = {
                    name: test["preprocess"]["files"][name]["location"]
                    for name in test["preprocess"]["files"]
                }
                deepMerge(test_files, preprocess_files)

            if "commands" in test["preprocess"]:
                commands = test["preprocess"]["commands"]
            elif "command" in test["preprocess"]:
                commands = [test["preprocess"]["command"]]
            self._runCommands(
                output,
                commands,
                self.host_platform,
                programs,
                model,
                test,
                model_files,
                input_files,
                None,
                None,
                test_files,
                -1,
                converter,
            )

        tgt_input_files = (
            platform.copyFilesToPlatform(input_files) if input_files else None
        )
        shared_libs = None
        if "shared_libs" in info:
            shared_libs = platform.copyFilesToPlatform(
                info["shared_libs"], copy_files=first_iteration
            )

        tgt_model_files = platform.copyFilesToPlatform(
            model_files, copy_files=first_iteration
        )

        tgt_result_files = None
        if "output_files" in test:
            tgt_result_files = {
                name: test["output_files"][name]["location"]
                for name in test["output_files"]
            }

        total_num = test["iter"]

        if "platform_args" in test:
            platform_args = test["platform_args"]
        elif "platform_args" in model:
            platform_args = model["platform_args"]
        else:
            platform_args = {}

        if "timeout" in model:
            platform_args["timeout"] = model["timeout"]
        if "timeout" in test:
            platform_args["timeout"] = test["timeout"]

        program = programs["program"] if "program" in programs else ""
        if test["metric"] == "power":
            platform_args["power"] = True
            method = test.get("method")
            platform_args["method"] = method

            if method == "software":
                power_util = software_power.PowerUtil(
                    platform, test.get("collection_time", 300)
                )
            else:
                # FIXME "Monsoon" was unimportable
                from utils.monsoon_power import collectPowerData

            # in power metric, the output is ignored
            total_num = 0
            platform.killProgram(program)

        if test.get("env", False):
            platform_args["env"] = test["env"]

        if platform.getType() == "host":
            # Fix the number of threads
            if not platform_args.get("env", False):
                platform_args["env"] = {}
            MKL_NUM_THREADS = test.get("MKL_NUM_THREADS", 1)
            OMP_NUM_THREADS = test.get("OMP_NUM_THREADS", 1)
            if MKL_NUM_THREADS > 0:
                platform_args["env"]["MKL_NUM_THREADS"] = MKL_NUM_THREADS
            if OMP_NUM_THREADS > 0:
                platform_args["env"]["OMP_NUM_THREADS"] = OMP_NUM_THREADS
            # Randomly select one cpu core from logic cpu #4 to #13.
            cpu_core = test.get("cpu-list", random.randint(5, 14))
            if isinstance(test["commands"], list) and cpu_core > 0:
                test["commands"][-1] = " ".join(
                    ["taskset", "--cpu-list", str(cpu_core), test["commands"][-1]]
                )

        self._runCommands(
            output,
            test["commands"],
            platform,
            programs,
            model,
            test,
            tgt_model_files,
            tgt_input_files,
            tgt_result_files,
            shared_libs,
            test_files,
            total_num,
            converter,
            platform_args=platform_args,
            main_command=True,
        )

        if test["metric"] == "power":
            if test.get("method") == "software":
                output = power_util.collect()
            else:
                collection_time = (
                    test["collection_time"] if "collection_time" in test else 180
                )
                voltage = float(test["voltage"]) if "voltage" in test else 4.0
                output = collectPowerData(
                    platform.platform_hash,
                    collection_time,
                    voltage,
                    test["iter"],
                    self.args.monsoon_map,
                )
                platform.waitForDevice(20)
                # kill the process if exists
                platform.killProgram(program)

        # remove the files before copying out the output files
        # this will save some time in ios platform, since in ios
        # all files are copied back to the host system
        if len(output) > 0:
            if input_files is not None:
                platform.delFilesFromPlatform(tgt_input_files)
            if last_iteration:
                platform.delFilesFromPlatform(tgt_model_files)
                platform.delFilesFromPlatform(tgt_program_files)
                if shared_libs is not None:
                    platform.delFilesFromPlatform(shared_libs)

        output_files = None
        if "output_files" in test:
            target_dir = os.path.join(self.tempdir, "output")
            shutil.rmtree(target_dir, True)
            os.makedirs(target_dir)
            output_files = platform.moveFilesFromPlatform(tgt_result_files, target_dir)

        platform.postprocess()

        if "postprocess" in test:
            if (
                "files" in test["postprocess"]
                and "program" in test["preprocess"]["files"]
            ):
                host_program_path = test["postprocess"]["files"]["program"]["location"]
                os.chmod(host_program_path, 0o777)

            # will deprecate in the future
            if "files" in test["postprocess"]:
                postprocess_files = {
                    name: test["postprocess"]["files"][name]["location"]
                    for name in test["postprocess"]["files"]
                }
                deepMerge(test_files, postprocess_files)

            commands = None
            if "commands" in test["postprocess"]:
                commands = test["postprocess"]["commands"]
            elif "command" in test["postprocess"]:
                commands = [test["postprocess"]["command"]]

            self._runCommands(
                output,
                commands,
                self.host_platform,
                programs,
                model,
                test,
                model_files,
                input_files,
                output_files,
                None,
                test_files,
                -1,
                converter,
            )

        if "postprocess" in model and last_iteration:
            commands = model["postprocess"]["commands"]
            self._runCommands(
                output,
                commands,
                self.host_platform,
                programs,
                model,
                test,
                model_files,
                None,
                None,
                None,
                None,
                -1,
                converter,
            )

        # after everything is done, some of the output files may
        # contain metrics that can be processed. Those files have
        # field converter, and specify which convert to use to
        # convert the metrics
        if output_files:
            to_upload = {}
            for filename in output_files:
                file = output_files[filename]
                output_file_spec = test["output_files"][filename]
                # if files should be uploaded, upload and add location to meta data.
                if output_file_spec.get("upload", False):
                    to_upload.update({filename: file})
                # if output_file can be converted for data, convert and merge output.
                converter = output_file_spec.get("converter")
                if not converter:
                    continue
                assert "name" in converter, "converter field must have a name"
                assert (
                    converter["name"] in self.converters
                ), "Unknown converter {}".format(converter["name"])
                converter_class = self.converters[converter["name"]]
                args = converter.get("args")
                with open(file, "r") as f:
                    content = f.read()
                convert = converter_class()
                results, _ = convert.collect(content, args)
                one_output = convert.convert(results)
                deepMerge(output, one_output)
            if to_upload:
                output_file_uploader = FileUploader("output_files").get_uploader()
                output_file_meta = {}
                for filename, file in to_upload.items():
                    try:
                        getLogger().info(f"Uploading {filename} ({file}) to manifold")
                        url = output_file_uploader.upload_file(file)
                        output_file_meta.update({filename: url})
                        getLogger().info(f"{file} uploaded to {url}")
                    except Exception:
                        getLogger().exception(
                            f"Could not upload output file {file}. Skipping."
                        )
                if output_file_meta:
                    if "output_files" in output["meta"]:
                        output["meta"]["output_files"].update(output_file_meta)
                    else:
                        output["meta"].update({"output_files": output_file_meta})

        return output, output_files

    @abc.abstractmethod
    def composeRunCommand(
        self,
        commands,
        platform,
        programs,
        model,
        test,
        model_files,
        input_files,
        output_files,
        shared_libs,
        test_files=None,
        main_command=False,
    ):
        if commands is None or not isinstance(commands, list):
            return None
        files = input_files.copy() if input_files is not None else {}
        files.update(output_files if output_files is not None else {})
        files.update(test_files if test_files is not None else {})
        extra_arguments = " " + model["command_args"] if "command_args" in model else ""
        string_map = json.loads(self.args.string_map) if self.args.string_map else {}
        composed_commands = []

        for command in commands:
            more_args = extra_arguments if "{program}" in command else ""
            command = self._getReplacedCommand(
                command, files, model, test, programs, model_files
            )
            command += more_args
            # extra args only applied for main_command
            if main_command and len(commands) == 1 and "pep_extra_args" in string_map:
                command += " " + string_map["pep_extra_args"]

            composed_commands.append(command)
        return composed_commands

    def _getReplacedCommand(self, command, files, model, test, programs, model_files):
        pattern = re.compile(r"\{([\w|\.]+)\}")
        repeat = True
        while repeat:
            repeat = False
            results = []
            for m in pattern.finditer(command):
                results.append(
                    {"start": m.start(), "end": m.end(), "content": m.group(1)}
                )
            results.reverse()
            for res in results:
                replace = self._getMatchedString(test, res["content"], files)
                if replace is None:
                    # TODO: handle shared libraries
                    replace = self._getMatchedString(model, res["content"], model_files)
                if replace is None:
                    replace = self._getMatchedString(programs, res["content"])

                if replace:
                    command = command[: res["start"]] + replace + command[res["end"] :]
                    repeat = True
        return command

    def _getMatchedString(self, root, match, files=None):
        if not isinstance(root, dict):
            return None
        if match in root:
            return getString(root[match])
        # split on .
        fields = match.split(".")
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
                return getString(files[fields[-1]])
        assert isinstance(entry, string_types), (
            "Output {}".format(entry) + " is not string type"
        )
        return getString(entry)

    @abc.abstractmethod
    def runOnPlatform(self, total_num, cmd, platform, platform_args, converter):
        raise NotImplementedError("Child class need to implement runOnPlatform")

    def _runCommands(
        self,
        output,
        commands,
        platform,
        programs,
        model,
        test,
        model_files,
        input_files,
        output_files,
        shared_libs,
        test_files,
        total_num,
        converter,
        platform_args=None,
        main_command=False,
    ):
        if platform_args is None:
            platform_args = {}
        if test and test.get("log_output", False):
            platform_args["log_output"] = True
        if self.args.timeout > 0 and "timeout" not in platform_args:
            platform_args["timeout"] = self.args.timeout
        cmds = self.composeRunCommand(
            commands,
            platform,
            programs,
            model,
            test,
            model_files,
            input_files,
            output_files,
            shared_libs,
            test_files,
            main_command,
        )
        profiling_enabled = False
        profiling_args = {}
        if "profiler" in test:
            profiling_enabled = test["profiler"].get("enabled", False)
        if profiling_enabled:
            # test[] is potentially raw user input so we need to ensure
            # ensure all fields are populated so we don't have to check elsewhere
            profiling_args = deepcopy(test["profiler"])
            types = profiling_args.get("types", ["cpu"])
            getLogger().info(f"platform = '{platform}', type(platform) = {type(platform)}.")
            default_profiler = (
                "xctrace"
                if platform == "ios"
                else "simpleperf"
                if ["cpu"] == types
                else "perfetto"
                if PerfettoAnySupported(types)
                else "<unspecified>"
            )
            profiler = profiling_args.setdefault("profiler", default_profiler)
            default_type = "memory" if profiler == "perfetto" else "cpu"
            profiling_args.setdefault("types", [default_type])
            profiling_args.setdefault("options", {})
            platform_args["model_name"] = getModelName(model)
        for idx, cmd in enumerate(cmds):
            # note that we only enable profiling for the last command
            # of the main commands.
            platform_args["profiling_args"] = (
                profiling_args
                if (profiling_enabled and main_command and idx == len(cmds) - 1)
                else {"enabled": False}
            )
            one_output = self.runOnPlatform(
                total_num, cmd, platform, platform_args, converter
            )
            deepMerge(output, one_output)

    @abc.abstractmethod
    def verifyBenchmarkFile(self, benchmark, filename, is_post):
        return None

    def rewriteBenchmarkTests(self, benchmark, filename):
        pass

    def _separatePrograms(self, program_files, commands):
        if commands is None or not isinstance(commands, list):
            return program_files, {}
        tgt_program_files = {}
        for command in commands:
            for name in program_files:
                if "{" + name + "}" in command:
                    tgt_program_files[name] = program_files[name]
        host_program_files = {
            name: program_files[name]
            for name in program_files
            if name not in tgt_program_files
        }
        return tgt_program_files, host_program_files

    def _createHostDir(self):
        hostdir = os.path.join(self.tempdir, "host")
        i = 0
        while os.path.exists(hostdir):
            hostdir = os.path.join(self.tempdir, "host" + str(i))
            i = i + 1
        os.makedirs(hostdir, 0o777)
        return hostdir

    def _replaceStringMap(self, root, platform, program_path, stringmap_from_info):
        try:
            # backward compatible
            string_map = (
                json.loads(self.args.string_map) if self.args.string_map else {}
            )

            info_string_map = (
                json.loads(stringmap_from_info) if stringmap_from_info else {}
            )
        except Exception:
            string_map = (
                ast.literal_eval(self.args.string_map) if self.args.string_map else {}
            )
            info_string_map = stringmap_from_info if stringmap_from_info else {}

        deepMerge(string_map, info_string_map)

        string_map["TGTDIR"] = platform.getOutputDir()
        string_map["HOSTDIR"] = self._createHostDir()
        string_map["FAIPEPROOT"] = getFAIPEPROOT()
        string_map["DEVICEHASH"] = platform.platform_hash
        if program_path:
            string_map["BUILDDIR"] = program_path

        for name in string_map:
            value = string_map[name]
            deepReplace(root, "{" + name + "}", value)
