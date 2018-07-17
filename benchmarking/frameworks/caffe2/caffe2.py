#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import collections
import copy
import json
import os
import re

from frameworks.framework_base import FrameworkBase
from utils.custom_logger import getLogger


class Caffe2Framework(FrameworkBase):
    IDENTIFIER = 'Caffe2Observer '
    NET = 'NET'

    def __init__(self, tempdir):
        super(Caffe2Framework, self).__init__()
        self.tempdir = tempdir + "/" + self.getName()
        os.makedirs(self.tempdir, 0o777)
        # cannot have any variable pass among methods

    def getName(self):
        return "caffe2"

    def runBenchmark(self, info, benchmark, platform):
        output, output_files = \
            super(Caffe2Framework, self).runBenchmark(info, benchmark,
                                                      platform)
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
            output_files = []
            num = self._checkNumFiles(input_files, source, num, True)
            if "output_files" in test:
                output_files = test["output_files"]
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

    def _checkNumFiles(self, files, source, num, is_input):
        new_num = num
        ftype = "input" if is_input else "output"
        for name in files:
            fs = files[name]
            if isinstance(fs, list):
                if new_num < 0:
                    new_num = len(fs)
                else:
                    assert len(fs) == new_num, \
                        "The number of specified {} files ".format(ftype) + \
                        "in blob {} do not ".format(name) + \
                        "match in all input blobs in benchmark " + \
                        "{}.".format(source)
            else:
                new_num = 1

        return new_num

    def composeRunCommand(self, platform, program, test, model_files,
                          input_files, shared_libs):
        cmd = [program,
               "--net", model_files["predict"],
               "--warmup", test["warmup"],
               "--iter", test["iter"]
               ]
        if "init" in model_files:
            cmd.append("--init_net")
            cmd.append(model_files["init"])
        if input_files:
            inputs = ",".join(list(input_files.keys()))
            cmd.extend(["--input_file",
                        ",".join(list(input_files.values()))])
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
            outputs = ",".join(list(test["output_files"].keys()))
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

    def runOnPlatform(self, total_num, cmd, platform, platform_args):
        results = []
        repeat = True
        while repeat:
            output = platform.runBenchmark(cmd, platform_args=platform_args)
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
        valid_runs = 0
        valid_run_idx = []
        while (i < len(useful_rows)):
            row = useful_rows[i]
            valid_row = row[(row.find(self.IDENTIFIER) +
                            len(self.IDENTIFIER)):]
            try:
                result = json.loads(valid_row)
                if "NET" in result:
                    valid_runs += 1
                    valid_run_idx.append(i)
                results.append(result)
            except Exception as e:
                # bypass one line
                getLogger().info(
                        "Skip one row %s \n Exception: %s" %
                        (valid_row, str(e))
                        )
                pass
            i += 1

        if valid_runs > total_num:
            # Android 5 has an issue that logcat -c does not clear the entry
            results = results[valid_run_idx[valid_runs-total_num]:]
        elif valid_runs < total_num:
            if len(results) > prev_num:
                getLogger().info(
                        "%d items collected. Still missing %d runs. "
                        "Collect again." %
                        (len(results) - prev_num, total_num - valid_runs))
                return True
            else:
                getLogger().info(
                        "No new items collected, finish collecting...")
        return False

    def _processDelayData(self, data):
        details = collections.defaultdict(
            lambda: collections.defaultdict(list))
        pattern = re.compile(r"^ID_(\d+)_([a-zA-Z0-9]+)_[\w/]+")
        for d in data:
            for k, v in d.items():
                for kk, vv in v.items():
                    key = k + " " + kk
                    if "info_string" in vv:
                        if "info_string" in details[key]:
                            assert details[key]["info_string"] == vv["info_string"], \
                                "info_string values for {} ".format(key) + \
                                "do not match.\n" + \
                                "Current info_string:\n{}\n ".format(details[key]["info_string"]) + \
                                "does not match new info_string:\n{}".format(vv["info_string"])
                        else:
                            details[key]["info_string"] = vv["info_string"]
                    else:
                        details[key]["values"].append(float(vv["value"]))
                    details[key]["type"] = k
                    # although it is declared as list
                    details[key]["metric"] = kk
                    details[key]["unit"] = str(vv["unit"])
                    match = pattern.match(k)
                    if match:
                        # per layer timing
                        details[key]["id"] = [match.group(1)]
                        details[key]["operator"] = [match.group(2)]
                    else:
                        # whole graph timing
                        assert key == self.NET + " " + kk
        return details
