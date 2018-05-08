#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


import copy
import hashlib
import json
import os
import requests
import shutil
from utils.arg_parse import getArgs
from utils.custom_logger import getLogger


class BenchmarkCollector(object):
    def __init__(self, model_cache):

        if not os.path.isdir(model_cache):
            os.makedirs(model_cache)
        self.model_cache = model_cache

    def collectBenchmarks(self, info, source):
        assert os.path.isfile(source), "Source {} is not a file".format(source)
        with open(source, 'r') as f:
            content = json.load(f)

        meta = content["meta"] if "meta" in content else {}
        if "meta" in info:
            self._deepMerge(meta, info["meta"])
        benchmarks = []

        if "benchmarks" in content:
            path = os.path.abspath(os.path.dirname(source))
            assert "meta" in content, "Meta field is missing in benchmarks"
            for benchmark_file in content["benchmarks"]:
                benchmark_file = path + "/" + benchmark_file
                self._collectOneBenchmark(benchmark_file,
                                          meta, benchmarks, info)
        else:
            self._collectOneBenchmark(source, meta, benchmarks, info)

        for b in benchmarks:
            self._verifyBenchmark(b, b["path"], True)
        return benchmarks

    def _verifyBenchmark(self, benchmark, filename, is_post):
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

    def _collectOneBenchmark(self, source, meta, benchmarks, info):
        assert os.path.isfile(source), \
            "Benchmark {} does not exist".format(source)
        with open(source, 'r') as b:
            one_benchmark = json.load(b)

        self._verifyBenchmark(one_benchmark, source, False)

        # Adding path to benchmark file
        one_benchmark["path"] = os.path.abspath(source)

        if meta:
            self._deepMerge(one_benchmark["model"], meta)
        if "commands" in info:
            if "commands" not in one_benchmark["model"]:
                one_benchmark["model"]["commands"] = {}
            self._deepMerge(one_benchmark["model"]["commands"], info["commands"])

        if "model" in benchmarks:
            self._verifyModel(one_benchmark, source)

        self._updateTests(one_benchmark, source)
        if len(one_benchmark["tests"]) == 1:
            benchmarks.append(one_benchmark)
        else:
            tests = copy.deepcopy(one_benchmark["tests"])
            one_benchmark["tests"] = []
            for test in tests:
                new_benchmark = copy.deepcopy(one_benchmark)
                new_benchmark["tests"].append(test)
                benchmarks.append(new_benchmark)

    def _verifyModel(self, one_benchmark, filename):
        model = one_benchmark["model"]
        model_dir = self.model_cache + "/" + model["format"] + "/" + \
            model["name"] + "/"
        if not os.path.isdir(model_dir):
            os.makedirs(model_dir)
        cached_models = {}
        update_json = False
        for f in model["files"]:
            field = model["files"][f]
            cached_model_name = \
                self._getModelFilename(field, model_dir, None)
            cached_models[f] = cached_model_name
            if not os.path.isfile(cached_model_name) or \
                    self._calculateMD5(cached_model_name) != field["md5"]:
                update_json |= self._copyFile(field, model_dir,
                                              cached_model_name, filename)

        if update_json:
            s = json.dumps(one_benchmark, indent=2, sort_keys=True)
            with open(filename, "w") as f:
                f.write(s)
            getLogger().info("Model {} is changed. ".format(model["name"]) +
                             "Please update the meta json file.")
            for f in model["files"]:
                cached_model_name = \
                    self._getModelFilename(field, model_dir, None)
                cached_models[f] = cached_model_name

        one_benchmark["model"]["cached_models"] = cached_models

    def _calculateMD5(self, model_name):
        m = hashlib.md5()
        m.update(open(model_name, 'rb').read())
        md5 = m.hexdigest()
        return md5

    def _copyFile(self, field, model_dir, cached_model_name, source):
        location = field["location"]
        if location[0:4] == "http":
            getLogger().info("Downloading {}".format(location))
            r = requests.get(location)
            if r.status_code == 200:
                with open(cached_model_name, 'wb') as f:
                    f.write(r.content)
        else:
            filename = self._getAbsFilename(location, source)
            shutil.copyfile(filename, cached_model_name)
        assert os.path.isfile(cached_model_name), \
            "File {} cannot be retrieved".format(cached_model_name)
        # verify the md5 matches the file downloaded
        md5 = self._calculateMD5(cached_model_name)
        if md5 != field["md5"]:
            getLogger().info("Source file {} is changed, ".format(location) +
                             " updating MD5. " +
                             "Please commit the updated json file.")
            new_cached_model_name = self._getModelFilename(field,
                                                           model_dir, md5)
            shutil.move(cached_model_name, new_cached_model_name)
            field["md5"] = md5
            return True
        return False

    def _getModelFilename(self, field, model_dir, md5):
        fn = os.path.splitext(field["filename"])
        cached_model_name = model_dir + "/" + \
            fn[0] + "_" + (md5 if md5 else field["md5"]) + fn[1]
        return cached_model_name

    def _updateTests(self, one_benchmark, source):
        if one_benchmark["tests"][0]["metric"] == "generic":
            return
        tests = one_benchmark.pop("tests")
        # dealing with multiple inputs
        new_tests = self._replicateTestsOnDims(tests, source)

        # dealing with multiple input files
        new_tests = self._replicateTestsOnFiles(new_tests, source)

        # Update identifiers
        self._updateNewTestFields(new_tests, one_benchmark)
        one_benchmark["tests"] = new_tests

    def _replicateTestsOnDims(self, tests, source):
        new_tests = []
        for test in tests:
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

    def _getAbsFilename(self, filename, source):
        if filename[0:2] == "//":
            assert getArgs().root_model_dir is not None, \
                "When specifying relative directory, the " \
                "--root_model_dir must be specified."
            return getArgs().root_model_dir + filename[1:]
        elif filename[0] != "/":
            abs_dir = os.path.dirname(os.path.abspath(source)) + "/"
            return abs_dir + filename
        else:
            return filename

    def _updateRelativeDirectory(self, files, source):
        for name in files:
            value = files[name]
            if isinstance(value, str):
                files[name] = [value]
            files[name] = [self._getAbsFilename(filename, source)
                           for filename in files[name]]
        return files

    def _replicateTestsOnFiles(self, tests, source):
        new_tests = []
        for test in tests:
            num = -1
            if "input_files" not in test:
                new_tests.append(copy.deepcopy(test))
                continue

            input_files = self._updateRelativeDirectory(test["input_files"],
                                                        source)
            output_files = self._updateRelativeDirectory(test["output_files"],
                                                         source)
            test["input_files"] = input_files
            test["output_files"] = output_files
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
                for f in fs:
                    self._checkFileExists(name, f, source, is_input)
            else:
                new_num = 1
                self._checkFileExists(name, fs, source, is_input)

        return new_num

    def _checkFileExists(self, name, fs, source, is_input):
        assert isinstance(fs, str), \
            "The file {} : {} should be a ".format(name, fs) + \
            "string, in benchmark {}.".format(source)
        assert os.path.isfile(fs), \
            "{} file ".format("Input" if is_input else "Output") + \
            "{} : {} does not exsit in ".format(name, fs) + \
            "benchmark {}".format(source)

    def _updateNewTestFields(self, tests, one_benchmark):
        idx = 0
        for test in tests:
            identifier = test["identifier"].replace("{ID}", str(idx))
            test["identifier"] = identifier
            idx += 1

        if "commands" in one_benchmark["model"]:
            for test in tests:
                if "commands" not in test:
                    test["commands"] = {}
                self._deepMerge(test["commands"],
                                one_benchmark["model"]["commands"])

    def _deepMerge(self, tgt, src):
        if isinstance(src, list):
            # only handle simple lists
            for item in src:
                if item not in tgt:
                    tgt.append(copy.deepcopy(item))
        elif isinstance(src, dict):
            for name in src:
                m = src[name]
                if name not in tgt:
                    tgt[name] = copy.deepcopy(m)
                else:
                    self._deepMerge(tgt[name], m)
        else:
            # tgt has already specified a value
            # src does not override tgt
            return
