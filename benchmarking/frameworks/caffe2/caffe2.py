#!/usr/bin/env python3

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import collections
import copy
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

        cached_files = \
            platform.copyFilesToPlatform(model["cached_files"])
        input_files = None
        if "input_files" in test:
            input_files = platform.copyFilesToPlatform(test["input_files"])

        cmd = self._composeRunCommand(platform, program, test, cached_files,
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
            platform.delFilesFromPlatform(cached_files)
            platform.delFilesFromPlatform(program)
            if shared_libs is not None:
                platform.delFilesFromPlatform(shared_libs)
            if input_files is not None:
                platform.delFilesFromPlatform(input_files)
        return output, output_files

    def verifyBenchmarkFile(self, benchmark, filename, is_post):
        # model is now optional
        if "model" in benchmark:
            model = benchmark["model"]
            assert "files" in model, \
                "Files field is missing in benchmark {}".format(filename)
            assert "name" in model, \
                "Name field is missing in benchmark {}".format(filename)
            assert "format" in model, \
                "Format field is missing in benchmark {}".format(filename)

            for f in model["files"]:
                field = model["files"][f]
                assert "filename" in field, \
                    "Filename is missing in file" + \
                    " {} of benchmark {}".format(f, filename)
                assert "location" in field, \
                    "Location is missing in file" + \
                    " {} of benchmark {}".format(f, filename)
                assert "md5" in field, \
                    "MD5 is missing in file" + \
                    " {} of benchmark {}".format(f, filename)

        # tests is mandatory
        assert "tests" in benchmark, \
            "Tests field is missing in benchmark {}".format(filename)
        tests = benchmark["tests"]

        if is_post:
            assert len(tests) == 1, "After rewrite, only one test in " + \
                "one benchmark."
        else:
            assert len(tests) > 0, "Tests cannot be empty"

        is_generic_test = tests[0]["metric"] == "generic"

        for test in tests:
            assert "metric" in test, "Metric field is missing in " + \
                "benchmark {}".format(filename)

            # no check is needed if the metric is generic
            if is_generic_test:
                assert test["metric"] == "generic", "All tests must be generic"
                continue

            assert "iter" in test, "Iter field is missing in benchmark " + \
                "{}".format(filename)
            assert "warmup" in test, "Warmup field is missing in " + \
                "benchmark {}".format(filename)

            assert "identifier" in test, "Identifier field is missing in " + \
                "benchmark {}".format(filename)

            assert "inputs" in test, "Inputs field is missing in " + \
                "benchmark {}".format(filename)

            num = -1
            for ip_name in test["inputs"]:
                ip = test["inputs"][ip_name]
                assert "shapes" in ip, "Shapes field is missing in" + \
                    " input {}".format(ip_name) + \
                    " of benchmark {}".format(filename)
                assert "type" in ip, \
                    "Type field is missing in input {}".format(ip_name) + \
                    " of benchmark {}".format(filename)
                assert isinstance(ip["shapes"], list), \
                    "Shape field should be a list. However, input " + \
                    "{} of benchmark is not.".format(ip_name, filename)

                dims = -1
                for item in ip["shapes"]:
                    assert isinstance(item, list), \
                        "Shapes must be a list of list."
                    if dims < 0:
                        dims = len(item)
                    else:
                        assert dims == len(item), \
                            "All shapes of one data must have " + \
                            "the same dimension"

                if num < 0:
                    num = len(ip["shapes"])
                else:
                    assert len(ip["shapes"]) == num, "The shapes of " + \
                        "input {} ".format(ip_name) + \
                        "are not of the same dimension in " + \
                        "benchmark {}".format(filename)

            if "input_files" in test:
                assert "output_files" in test, \
                    "Input files are specified, but output files are not " + \
                    "specified in the benchmark {}".format(filename)

    def rewriteBenchmarkTests(self, benchmark, filename):
        tests = benchmark.pop("tests")
        new_tests = self._replicateTestsOnDims(tests, filename)
        # dealing with multiple input files
        new_tests = self._replicateTestsOnFiles(new_tests, filename)
        benchmark["tests"] = new_tests

    def _replicateTestsOnFiles(self, tests, source):
        new_tests = []
        for test in tests:
            num = -1
            if "input_files" not in test:
                new_tests.append(copy.deepcopy(test))
                continue

            input_files = test["input_files"]
            output_files = test["output_files"]
            num = self._checkNumFiles(input_files, source, num, True)
            num = self._checkNumFiles(output_files, source, num, False)

            for i in range(num):
                t = copy.deepcopy(test)
                for iname in input_files:
                    t["input_files"][iname] = test["input_files"][iname][i]
                for oname in output_files:
                    t["output_files"][oname] = \
                        test["output_files"][oname][i]
                    new_tests.append(t)
        return new_tests

    def _replicateTestsOnDims(self, tests, source):
        new_tests = []
        for test in tests:
            if "inputs" not in test:
                new_tests.append(copy.deepcopy(test))
                continue

            num = -1
            for ip_name in test["inputs"]:
                ip = test["inputs"][ip_name]
                if num < 0:
                    num = len(ip["shapes"])
                    break

            if num == 1:
                new_tests.append(copy.deepcopy(test))
            else:
                for i in range(num):
                    t = copy.deepcopy(test)
                    for ip_name in t["inputs"]:
                        t["inputs"][ip_name]["shapes"] = \
                            [test["inputs"][ip_name]["shapes"][i]]
                    new_tests.append(t)
        return new_tests

    def _composeRunCommand(self, platform, program, test, cached_files,
                           input_files, shared_libs):
        cmd = [program,
               "--net", cached_files["predict"],
               "--warmup", test["warmup"],
               "--iter", test["iter"]
               ]
        if "init" in cached_files:
            cmd.append("--init_net")
            cmd.append(cached_files["init"])
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
        details = collections.defaultdict(
            lambda: collections.defaultdict(list))
        for d in data:
            for k, v in d.items():
                # Value is collected in milliseconds, add value in microseconds
                details[k]["values"].append(v * 1000)
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
