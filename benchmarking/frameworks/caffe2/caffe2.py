#!/usr/bin/env python3.6

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


class Caffe2Framework(FrameworkBase):
    DELAYS_START = 'Delay Start'
    DELAYS_END = 'Delay End'
    IDENTIFIER = 'Caffe2Observer '
    NET_DELAY = 'NET_DELAY'

    def __init__(self, tempdir):
        super(Caffe2Framework, self).__init__()
        self.tempdir = tempdir + "/" + self.getName()
        os.makedirs(self.tempdir, 0o777, True)
        # cannot have any variable pass among methods

    def getName(self):
        return "caffe2"

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

        cached_models = \
            platform.copyFilesToPlatform(model["cached_models"])
        input_files = None
        if "input_files" in test:
            input_files = platform.copyFilesToPlatform(test["input_files"])

        cmd = self._composeRunCommand(platform, program, test, cached_models,
                                      input_files, shared_libs)
        total_num = test["iter"]
        if "commands" in test and \
                "caffe2" in test["commands"] and \
                "run_individual" in test["commands"]["caffe2"] and \
                test["commands"]["caffe2"]["run_individual"] == "true":
            total_num *= 2
        output = self._runOnPlatform(total_num, cmd, platform)
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

        if len(output) > 0:
            platform.delFilesFromPlatform(cached_models)
            platform.delFilesFromPlatform(program)
            if shared_libs is not None:
                platform.delFilesFromPlatform(shared_libs)
            if input_files is not None:
                platform.delFilesFromPlatform(input_files)
        return output, output_files

    def _composeRunCommand(self, platform, program, test, cached_models,
                           input_files, shared_libs):
        cmd = [program,
               "--net", cached_models["predict"],
               "--warmup", test["warmup"],
               "--iter", test["iter"]
               ]
        if "init" in cached_models:
            cmd.append("--init_net")
            cmd.append(cached_models["init"])
        if input_files:
            inputs = ",".join(list(input_files.keys()))
            cmd.extend(["--input_file", ",".join(list(input_files.values()))])
        else:
            inputs = ",".join(list(test["inputs"].keys()))
            input_dims = [
                ",".join([str(a) for a in test["inputs"][x]["shapes"][0]])
                for x in test["inputs"]]
            input_dims = ";".join(input_dims)
            cmd.extend(["--input_dims", input_dims])
        cmd.extend(["--input", inputs])
        cmd.extend(["--input_type",
                   list(test["inputs"].values())[0]["type"]])
        if "output_files" in test:
            outputs = ",".join(list(test["output_files"]))
            cmd.extend(["--output", outputs])
            cmd.extend(["--text_output", "true"])
            cmd.extend(["--output_folder", platform.getOutputDir()])
        if "commands" in test:
            if "caffe2" in test["commands"]:
                for key in test["commands"]["caffe2"]:
                    val = test["commands"]["caffe2"][key]
                    cmd.extend(["--" + key, val])

        if shared_libs:
            cmd = ["export", "LD_LIBRARY_PATH=$\{LD_LIBRARY_PATH\}:" +
                   os.path.dirname(shared_libs[0]), "&&"] + cmd
        cmd = [str(s) for s in cmd]
        return cmd

    def _runOnPlatform(self, total_num, cmd, platform):
        results = []
        repeat = True
        while repeat:
            output = platform.runBenchmark(cmd)
            repeat = self._collectDelayData(total_num, output, results)
        metric = self._processDelayData(results)
        return metric

    def _collectDelayData(self, total_num, output, results):
        if output is None:
            return False
        prev_num = len(results)
        rows = output.split('\n')
        useful_rows = [row for row in rows if row.find(self.IDENTIFIER) >= 0]
        i = 0
        while (i < len(useful_rows)):
            if (i < len(useful_rows) and
                    (useful_rows[i].find(self.DELAYS_START) >= 0)):
                result = {}
                i = self._parseDelayData(useful_rows, result, i)
                if (len(result) > 1) and (self.NET_DELAY in result):
                    # operator delay. Need to strip the net delay from it
                    del result[self.NET_DELAY]
                results.append(result)
            i += 1

        if len(results) > total_num:
            # Android 5 has an issue that logcat -c does not clear the entry
            results = results[-total_num:]
        elif len(results) < total_num:
            if len(results) > prev_num:
                getLogger().info(
                        "%d items collected. Still missing %d items. "
                        "Collect again." %
                        (len(results) - prev_num, total_num - len(results)))
                return True
            else:
                getLogger().info(
                        "No new items collected, finish collecting...")
        return False

    def _parseDelayData(self, rows, result, start_idx):
        assert rows[start_idx].find(self.DELAYS_START) >= 0, \
                "Does not find the start of the delay"
        i = start_idx+1
        while i < len(rows) and rows[i].find(self.DELAYS_END) < 0:
            row = rows[i]
            start_idx = row.find(self.IDENTIFIER) + len(self.IDENTIFIER)
            pair = row[start_idx:].strip().split(' - ')
            assert len(pair) == 2, \
                "Operator delay doesn't have two items: %s" % row
            unit_idx = pair[1].find("(")
            assert unit_idx > 0, "Unit is not specified"
            result[pair[0].strip()] = float(pair[1][:unit_idx-1].strip())
            i = i+1
        return i


    def _processDelayData(self, data):
        details = collections.defaultdict(lambda: collections.defaultdict(list))
        for d in data:
            for k, v in d.items():
                details[k]["values"].append(v)
        pattern = re.compile(r"^ID_(\d+)_([a-zA-Z0-9]+)_[\w/]+")
        for key in details:
            match = pattern.match(key)
            if match:
                # per layer timing
                details[key]["id"].append(match.group(1))
                details[key]["operator"].append(match.group(2))
            else:
                # whole graph timing
                assert key == self.NET_DELAY
        return details
