#!/usr/bin/env python

# pyre-unsafe

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
    def __init__(self, tempdir, args):
        self.tempdir = os.path.join(tempdir, self.getName())
        os.makedirs(self.tempdir, 0o777)

    def getName(self):
        return "oculus"

    def runBenchmark(self, info, benchmark, platform):
        tests = benchmark["tests"]
        assert len(tests) == 1, (
            "At this point, only one test should "
            + "exist in one benchmark. However, benchmark "
            + "{} doesn't.".format(benchmark["name"])
        )

        model = benchmark["model"]
        test = tests[0]
        assert set({"input_files", "output_files"}).issubset(test.keys())

        assert platform.getType() == "android", "Only android system is supported"
        platform.util.run("root")
        platform.util.run("remount")

        libraries = []
        if "libraries" in model:
            for entry in model["libraries"]:
                target = entry["target"] if "target" in entry else platform.util.dir
                libraries.append(
                    platform.copyFilesToPlatform(entry["location"], target)
                )

        assert "files" in model, "files field is required in model"

        model_file = {f: model["files"][f]["location"] for f in model["files"]}
        model_file = platform.copyFilesToPlatform(model_file)
        input_files = [f["location"] for f in test["input_files"]]
        inputs = platform.copyFilesToPlatform(input_files)
        outputs = [
            os.path.join(platform.getOutputDir(), t["filename"])
            for t in test["output_files"]
        ]
        # Always copy binary to /system/bin/ directory
        program = platform.copyFilesToPlatform(
            info["programs"]["program"]["location"],
            info["programs"]["program"]["dest_path"],
        )
        env_vars = info["programs"]["program"].get("env_variables", "")
        commands = self._composeRunCommand(
            env_vars, program, platform, test, inputs, outputs
        )
        platform.runBenchmark(commands, log_to_screen_only=True)

        target_dir = os.path.join(self.tempdir, "output")
        shutil.rmtree(target_dir, True)
        os.makedirs(target_dir)

        platform.delFilesFromPlatform(model_file)
        platform.delFilesFromPlatform(inputs)
        # Skip deleting the libraries, as they may be used by other binaries
        # platform.delFilesFromPlatform(libraries)
        platform.delFilesFromPlatform(program)
        # output files are removed after being copied back
        output_files = platform.moveFilesFromPlatform(outputs, target_dir)

        json_file = platform.moveFilesFromPlatform(
            os.path.join(platform.getOutputDir(), "report.json"), self.tempdir
        )
        with open(json_file) as f:
            json_content = json.load(f)

        result = {}
        for one_test in json_content:
            for one_entry in one_test:
                type = one_entry["type"]
                value = one_entry["value"]
                unit = one_entry["unit"]
                metric = one_entry["metric"]
                map_key = f"{type}_{metric}"
                if map_key in result:
                    entry = result[map_key]
                    if entry["unit"] is not None and entry["unit"] != unit:
                        getLogger().error(
                            "The unit do not match in different"
                            " test runs {} and {}".format(entry["unit"], unit)
                        )
                        entry["unit"] = None
                    if entry["metric"] is not None and entry["metric"] != metric:
                        getLogger().error(
                            "The metric do not match in "
                            " different test runs {} and {}".format(
                                entry["metric"], metric
                            )
                        )
                        entry["metric"] = None
                    entry["values"].append(value)
                else:
                    result[map_key] = {
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
        assert "model" in benchmark, "Model must exist in the benchmark {}".format(
            filename
        )
        assert (
            "name" in benchmark["model"]
        ), f"field name must exist in model in benchmark {filename}"
        assert (
            "format" in benchmark["model"]
        ), f"field format must exist in model in benchmark {filename}"
        assert "tests" in benchmark, "Tests field is missing in benchmark {}".format(
            filename
        )

        for test in benchmark["tests"]:
            assert (
                "input_files" in test
            ), f"inputs must exist in test in benchmark {filename}"
            assert (
                "output_files" in test
            ), f"outputs must exist in test in benchmark {filename}"
            assert "metric" in test, "metric must exist in test in benchmark {}".format(
                filename
            )

    def _composeRunCommand(self, env_vars, program, platform, test, inputs, outputs):
        cmd = [env_vars, program, "--json", platform.getOutputDir() + "report.json"]
        if len(inputs) > 0:
            cmd.extend(["--input", " ".join(inputs)])
        if len(outputs) > 0:
            cmd.extend(["--output", " ".join(outputs)])
        if "commands" in test:
            if "oculus" in test["commands"]:
                for key in test["commands"]["oculus"]:
                    val = test["commands"]["oculus"][key]
                    cmd.extend(["--" + key, str(val)])
        return " ".join(cmd)
