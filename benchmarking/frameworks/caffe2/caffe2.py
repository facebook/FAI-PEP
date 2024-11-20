#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import copy
import os

from frameworks.framework_base import FrameworkBase
from utils.custom_logger import getLogger
from utils.utilities import getRunStatus


class Caffe2Framework(FrameworkBase):
    IDENTIFIER = "Caffe2Observer "
    NET = "NET"

    def __init__(self, tempdir, args):
        super(Caffe2Framework, self).__init__(args)
        self.tempdir = os.path.join(tempdir, self.getName())
        os.makedirs(self.tempdir, 0o777)
        # cannot have any variable pass among methods

    def getName(self):
        return "caffe2"

    def runBenchmark(self, info, benchmark, platform):
        output, output_files = super(Caffe2Framework, self).runBenchmark(
            info, benchmark, platform
        )
        return output, output_files

    def verifyBenchmarkFile(self, benchmark, filename, is_post):
        # model is now optional
        if "model" in benchmark:
            model = benchmark["model"]
            assert "files" in model, "Files field is missing in benchmark {}".format(
                filename
            )
            assert "name" in model, "Name field is missing in benchmark {}".format(
                filename
            )
            assert "format" in model, "Format field is missing in benchmark {}".format(
                filename
            )

            for f in model["files"]:
                field = model["files"][f]
                assert "filename" in field, (
                    "Filename is missing in file"
                    + " {} of benchmark {}".format(f, filename)
                )
                assert "location" in field, (
                    "Location is missing in file"
                    + " {} of benchmark {}".format(f, filename)
                )
                if "md5" not in field:
                    assert not field["location"].startswith("//") or field[
                        "location"
                    ].startswith("//fbpkg"), (
                        "MD5 is missing in file"
                        + " {} of benchmark {}".format(f, filename)
                    )

        # tests is mandatory
        assert "tests" in benchmark, "Tests field is missing in benchmark {}".format(
            filename
        )
        tests = benchmark["tests"]

        if is_post:
            assert len(tests) == 1, (
                "After rewrite, only one test in " + "one benchmark."
            )
        else:
            assert len(tests) > 0, "Tests cannot be empty"

        is_generic_test = tests[0]["metric"] == "generic"

        for test in tests:
            assert "metric" in test, (
                "Metric field is missing in " + "benchmark {}".format(filename)
            )

            # no check is needed if the metric is generic
            if is_generic_test:
                assert test["metric"] == "generic", "All tests must be generic"
                continue

            if "iter" not in test:
                test["iter"] = -1
            if "warmup" not in test:
                test["warmup"] = -1

            assert "identifier" in test, (
                "Identifier field is missing in " + "benchmark {}".format(filename)
            )

            if "commands" in test or "command" in test or "arguments" in test:
                continue
            # for backward compatibility purpose
            assert "inputs" in test, (
                "Inputs field is missing in " + "benchmark {}".format(filename)
            )

            num = -1
            for ip_name in test["inputs"]:
                ip = test["inputs"][ip_name]
                assert "shapes" in ip, (
                    "Shapes field is missing in"
                    + " input {}".format(ip_name)
                    + " of benchmark {}".format(filename)
                )
                assert "type" in ip, "Type field is missing in input {}".format(
                    ip_name
                ) + " of benchmark {}".format(filename)
                assert isinstance(ip["shapes"], list), (
                    "Shape field should be a list. However, input "
                    + "{} of benchmark is not.".format(ip_name, filename)
                )

                dims = -1
                for item in ip["shapes"]:
                    assert isinstance(item, list), "Shapes must be a list of list."
                    if dims < 0:
                        dims = len(item)
                    else:
                        assert dims == len(item), (
                            "All shapes of one data must have " + "the same dimension"
                        )

                if num < 0:
                    num = len(ip["shapes"])
                else:
                    assert len(ip["shapes"]) == num, (
                        "The shapes of "
                        + "input {} ".format(ip_name)
                        + "are not of the same dimension in "
                        + "benchmark {}".format(filename)
                    )

    def rewriteBenchmarkTests(self, benchmark, filename):
        tests = benchmark.pop("tests")
        new_tests = self._replicateTestsOnDims(tests, filename)
        benchmark["tests"] = new_tests

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
                        t["inputs"][ip_name]["shapes"] = [
                            test["inputs"][ip_name]["shapes"][i]
                        ]
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
                    assert len(fs) == new_num, (
                        "The number of specified {} files ".format(ftype)
                        + "in blob {} do not ".format(name)
                        + "match in all input blobs in benchmark "
                        + "{}.".format(source)
                    )
            else:
                new_num = 1

        return new_num

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
        preprocess_files=None,
        main_command=False,
    ):
        cmds = super(Caffe2Framework, self).composeRunCommand(
            commands,
            platform,
            programs,
            model,
            test,
            model_files,
            input_files,
            output_files,
            shared_libs,
            preprocess_files,
            main_command,
        )
        if cmds:
            return cmds

        # old format, will deprecate
        cmd = [
            "--net",
            model_files["predict"],
            "--warmup",
            test["warmup"],
            "--iter",
            test["iter"],
        ]
        if "program" in programs:
            cmd = [programs["program"]] + cmd
        if "init" in model_files:
            cmd.append("--init_net")
            cmd.append(model_files["init"])
        if input_files:
            inputs = ",".join(list(input_files.keys()))
            cmd.extend(["--input_file", ",".join(list(input_files.values()))])
        else:
            inputs = ",".join(list(test["inputs"].keys()))
            input_dims = [
                ",".join([str(a) for a in test["inputs"][x]["shapes"][0]])
                for x in test["inputs"]
            ]
            input_dims = ";".join(input_dims)
            cmd.extend(["--input_dims", input_dims])
        cmd.extend(["--input", inputs])
        cmd.extend(["--input_type", list(test["inputs"].values())[0]["type"]])
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
            cmd = [
                "export",
                "LD_LIBRARY_PATH=$\{LD_LIBRARY_PATH\}:"
                + os.path.dirname(shared_libs[0]),
                "&&",
            ] + cmd
        cmd = " ".join(str(s) for s in cmd)
        return [cmd]

    def runOnPlatform(self, total_num, cmd, platform, platform_args, converter):
        if converter is None:
            converter = {
                "name": "json_with_identifier_converter",
                "args": {"identifier": self.IDENTIFIER},
            }

        converter_obj = self.converters[converter["name"]]()
        args = converter.get("args")
        results = []
        num = 0
        # emulate do...while... loop
        while True:
            output, meta = platform.runBenchmark(cmd, platform_args=platform_args)
            one_result, valid_run_idxs = converter_obj.collect(output, args)
            valid_run_idxs = [num + idx for idx in valid_run_idxs]
            num += len(valid_run_idxs)
            results.extend(one_result)
            if getRunStatus() != 0:
                getLogger().info("Execution failed, terminating")
                break
            if num < total_num:
                num_items = len(valid_run_idxs)
                if num_items > 0:
                    getLogger().info(
                        "%d items collected, Still missing %d "
                        "runs. Collect again." % (num_items, total_num - num)
                    )

                    continue
                else:
                    getLogger().info("No new items collected, " "finish collecting...")
            elif total_num >= 0 and num > total_num:
                # if collect more than the needed number, get the
                # latest entries. This may happen when the data in
                # the previous runs are not cleared. e.g. on some
                # android 5 devices. Or, it may happen when multiple
                # runs are needed to collect the desired number of
                # iterations
                results = results[valid_run_idxs[num - total_num] :]
            break
        metric = converter_obj.convert(results)
        metric["meta"] = meta
        return metric
