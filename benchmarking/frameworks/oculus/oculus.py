#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import json
import os
import shutil
from frameworks.framework_base import FrameworkBase
from utils.custom_logger import getLogger


class OculusFramework(FrameworkBase):
    def __init__(self, tempdir):
        self.tempdir = os.path.join(tempdir, self.getName())
        os.makedirs(self.tempdir, 0o777)

    def getName(self):
        return "oculus"

    def runBenchmark(self, info, benchmark, platform):
        tests = benchmark["tests"]
        assert len(tests) == 1, "At this point, only one test should " + \
            "exist in one benchmark. However, benchmark " + \
            "{} doesn't.".format(benchmark["name"])

        model = benchmark["model"]
        test = tests[0]
        assert set({"input_files", "output_files"}).issubset(test.keys())

        assert platform.getType() == "android", \
            "Only android system is supported"
        platform.adb.run("root")
        platform.adb.run("remount")

        libraries = []
        if "libraries" in model:
            for entry in model["libraries"]:
                target = entry["target"] \
                    if "target" in entry else platform.adb.dir
                libraries.append(platform.copyFilesToPlatform(
                    entry["location"], target))

        assert "files" in model, "files field is required in model"
        assert len(model["files"]) == 1, "only one file is specified in model"

        model_file = {f: model["files"][f]["location"] for f in model["files"]}
        model_file = platform.copyFilesToPlatform(model_file)
        for name in model_file:
            model_filename = model_file[name]
        input_files = [f["location"] for f in test["input_files"]]
        inputs = \
            platform.copyFilesToPlatform(input_files)
        outputs = [os.path.join(platform.getOutputDir(), t["filename"])
                   for t in test["output_files"]]
        # Always copy binary to /system/bin/ directory
        program = platform.copyFilesToPlatform(info["program"], "/system/bin/")
        commands = self._composeRunCommand(program, platform, model,
                                           model_filename, test,
                                           inputs, outputs)
        platform.runBenchmark(commands, log_to_screen_only=True)

        target_dir = os.path.join(self.tempdir, "output")
        shutil.rmtree(target_dir, True)
        os.makedirs(target_dir)

        platform.delFilesFromPlatform(model_file)
        platform.delFilesFromPlatform(inputs)
        platform.delFilesFromPlatform(libraries)
        platform.delFilesFromPlatform(program)
        # output files are removed after being copied back
        output_files = platform.moveFilesFromPlatform(outputs,
                                                      target_dir)

        json_file = platform.moveFilesFromPlatform(
            os.path.join(platform.getOutputDir(), "report.json"),
            self.tempdir)
        with open(json_file, 'r') as f:
            json_content = json.load(f)

        result = {}
        for one_test in json_content:
            for one_entry in one_test:
                type = one_entry["type"]
                value = one_entry["value"]
                unit = one_entry["unit"]
                metric = one_entry["metric"]
                if type in result:
                    entry = result[type]
                    if entry["unit"] is not None and entry["unit"] != unit:
                        getLogger().error("The unit do not match in different"
                                          " test runs {} and {}".
                                          format(entry["unit"], unit))
                        entry["unit"] = None
                    if entry["metric"] is not None and \
                            entry["metric"] != metric:
                        getLogger().error("The metric do not match in "
                                          " different test runs {} and {}".
                                          format(entry["metric"], metric))
                        entry["metric"] = None
                    entry["values"].append(value)
                else:
                    result[type] = {
                        "type": type,
                        "values": [value],
                        "unit": unit,
                        "metric": metric,
                    }
        # cleanup
        # platform.delFilesFromPlatform(program)
        # for input in test["input"]:
        #     platform.delFilesFromPlatform(input)
        return result, output_files

    def verifyBenchmarkFile(self, benchmark, filename, is_post):
        assert "model" in benchmark, \
            "Model must exist in the benchmark {}".format(filename)
        assert "name" in benchmark["model"], \
            "field name must exist in model in benchmark {}".format(filename)
        assert "format" in benchmark["model"], \
            "field format must exist in model in benchmark {}".format(filename)
        assert "tests" in benchmark, \
            "Tests field is missing in benchmark {}".format(filename)

        for test in benchmark["tests"]:
            assert "input_files" in test, \
                "inputs must exist in test in benchmark {}".format(filename)
            assert "output_files" in test, \
                "outputs must exist in test in benchmark {}".format(filename)
            assert "metric" in test, \
                "metric must exist in test in benchmark {}".format(filename)

    def _composeRunCommand(self, program, platform, model, model_filename,
                           test, inputs, outputs):
        cmd = [program,
               "--json", platform.getOutputDir() + "report.json",
               "--model", model["name"],
               "--modelfile", model_filename,
               "--input", ' ' .join(inputs),
               "--output", ' '.join(outputs)]
        if "commands" in test:
            if "oculus" in test["commands"]:
                for key in test["commands"]["oculus"]:
                    val = test["commands"]["oculus"][key]
                    cmd.extend(["--" + key, str(val)])
        return ' '.join(cmd)
