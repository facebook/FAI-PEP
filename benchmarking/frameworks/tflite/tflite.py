#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import os
import re

from frameworks.framework_base import FrameworkBase


class TFLiteFramework(FrameworkBase):
    def __init__(self, tempdir):
        super(TFLiteFramework, self).__init__()
        self.tempdir = tempdir + "/" + self.getName()
        os.makedirs(self.tempdir, 0o777)

    def getName(self):
        return "tflite"

    def runBenchmark(self, info, benchmark, platform):
        output, output_files = \
            super(TFLiteFramework, self).runBenchmark(info, benchmark,
                                                      platform)
        return output, output_files

    def verifyBenchmarkFile(self, benchmark, filename, is_post):
        assert "model" in benchmark, "Field model is missing in benchmark"
        assert "files" in benchmark["model"], \
            "Field files is missing in benchmark[model]"
        assert "graph" in benchmark["model"]["files"], \
            "Field graph is missing in benchmark[model][files]"

        assert "tests" in benchmark, "Field tests is missing in benchmark"
        for test in benchmark["tests"]:
            assert "inputs" in test, "Field inputs is missing in test"
            for layer in test["inputs"]:
                assert "shapes" in test["inputs"][layer], \
                    "Field shapes is missing in test[inputs][layer]"
            assert "warmup" in test, "Field warmup is missing in test"
            assert "iter" in test, "Field iter is missing in test"

    def composeRunCommand(self, platform, program, model, test, model_files,
                          input_files, output_files, shared_libs):
        cmd = super(TFLiteFramework, self).composeRunCommand(platform,
                                                             program,
                                                             model,
                                                             test,
                                                             model_files,
                                                             input_files,
                                                             output_files,
                                                             shared_libs)
        if cmd:
            return cmd
        input = None
        input_shape = None
        for layer in test["inputs"]:
            input = layer
            input_shape = ",".join(str(a) for a in
                                   test["inputs"][layer]["shapes"][0])
        cmd = [
            program,
            "--graph={}".format(model_files["graph"]),
            "--warmup_runs={}".format(test["warmup"]),
            "--num_runs={}".format(test["iter"]),
            "--input_layer={}".format(input),
            "--input_layer_shape={}".format(input_shape)
        ]
        if "commands" in test:
            if "tflite" in test["commands"]:
                for key in test["commands"]["tflite"]:
                    val = test["commands"]["tflite"][key]
                    cmd.extend(["--{}={}".format(key, val)])

        cmd = [str(s) for s in cmd]
        return cmd

    def runOnPlatform(self, total_num, cmd, platform, platform_args):
        output = platform.runBenchmark(cmd, platform_args=platform_args,
                                       log_to_screen_only=True)
        result = self._collectData(total_num, output)
        metric = self._processData(result)
        return metric

    def _collectData(self, total_num, output):
        if output is None:
            return False
        result = {}
        rows = output.split('\n')
        # only collect one data point for statistics
        # the actual run data should override the warmup data
        i = 0
        while i < len(rows):
            row = rows[i]
            if row[0:21] == "Running benchmark for":
                assert len(rows) > i+1, "Valid row cannot be found"
                data = rows[i+1]
                pattern = re.compile(r"^count=([\d|\.]+) first=([\d|\.]+) curr=([\d|\.]+) min=([\d|\.]+) max=([\d|\.]+) avg=([\d|\.]+) std=([\d|\.]+)")
                match = pattern.match(data)
                if match:
                    result["NET"] = {
                        "count": int(match.group(1)),
                        "min": float(match.group(4)),
                        "max": float(match.group(5)),
                        "avg": float(match.group(6)),
                        "std": float(match.group(7))
                    }
                else:
                    pattern = re.compile(r"^count=(\d+) curr=(\d+)")
                    match = pattern.match(data)
                    assert match, \
                        "No data is collected for {}".format(data)

                    result["NET"] = {
                        "count": int(match.group(1)),
                        "min": float(match.group(2)),
                        "max": float(match.group(2)),
                        "avg": float(match.group(2)),
                        "std": 0
                    }
            i += 1
        return result

    def _processData(self, data):
        assert len(data) == 1, "Only one line should be collected"
        result = {
            "type": "NET",
            "unit": "us",
            "metric": "latency",
            "num_runs": data["NET"]["count"],
            "summary": {
                "p0": data["NET"]["min"],
                "p100": data["NET"]["max"],
                "mean": data["NET"]["avg"],
                "stdev": data["NET"]["std"],
            }
        }
        results = {
            "NET latency": result
        }
        return results
