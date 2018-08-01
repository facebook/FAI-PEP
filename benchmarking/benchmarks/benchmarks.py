#!/usr/bin/env python

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
from utils.utilities import deepMerge


class BenchmarkCollector(object):
    def __init__(self, framework, model_cache):

        if not os.path.isdir(model_cache):
            os.makedirs(model_cache)
        self.model_cache = model_cache
        self.framework = framework

    def collectBenchmarks(self, info, source):
        assert os.path.isfile(source), "Source {} is not a file".format(source)
        with open(source, 'r') as f:
            content = json.load(f)

        meta = content["meta"] if "meta" in content else {}
        if "meta" in info:
            deepMerge(meta, info["meta"])
        if hasattr(getArgs(), "timeout"):
            meta["timeout"] = getArgs().timeout
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
        self.framework.verifyBenchmarkFile(benchmark, filename, is_post)

    def _collectOneBenchmark(self, source, meta, benchmarks, info):
        assert os.path.isfile(source), \
            "Benchmark {} does not exist".format(source)
        with open(source, 'r') as b:
            one_benchmark = json.load(b)

        self._verifyBenchmark(one_benchmark, source, False)

        self._updateFiles(one_benchmark, source)

        # following change should not appear in updated_json file
        if meta:
            deepMerge(one_benchmark["model"], meta)
        if "commands" in info:
            if "commands" not in one_benchmark["model"]:
                one_benchmark["model"]["commands"] = {}
            deepMerge(one_benchmark["model"]["commands"], info["commands"])

        self._updateTests(one_benchmark, source)
        # Add fields that should not appear in the saved benchmark file
        # Adding path to benchmark file
        one_benchmark["path"] = os.path.abspath(source)

        # One test per benchmark
        if len(one_benchmark["tests"]) == 1:
            benchmarks.append(one_benchmark)
        else:
            tests = copy.deepcopy(one_benchmark["tests"])
            one_benchmark["tests"] = []
            for test in tests:
                new_benchmark = copy.deepcopy(one_benchmark)
                new_benchmark["tests"].append(test)
                benchmarks.append(new_benchmark)

    # Update all files in the benchmark to absolute path
    # download the files if needed
    def _updateFiles(self, one_benchmark, filename):

        model = one_benchmark["model"]
        model_dir = self.model_cache + "/" + model["format"] + "/" + \
            model["name"] + "/"
        if not os.path.isdir(model_dir):
            os.makedirs(model_dir)
        collected_files = self._collectFiles(one_benchmark)
        update_json = False
        for file in collected_files:
            update_json |= self._updateOneFile(file, model_dir, filename)

        if update_json:
            s = json.dumps(one_benchmark, indent=2, sort_keys=True)
            with open(filename, "w") as f:
                f.write(s)
            getLogger().info("Model {} is changed. ".format(model["name"]) +
                             "Please update the meta json file.")

        # update the file field with the absolute path
        # needs to be after the file is updated
        for file in collected_files:
            cached_filename = \
                self._getDestFilename(file, model_dir)
            file["location"] = cached_filename

    def _collectFiles(self, benchmark):
        files = []
        if "model" in benchmark:
            if "files" in benchmark["model"]:
                self._collectOneGroupFiles(benchmark["model"]["files"], files)
            if "libraries" in benchmark["model"]:
                self._collectOneGroupFiles(benchmark["model"]["libraries"],
                                           files)

        for test in benchmark["tests"]:
            if "input_files" in test:
                self._collectOneGroupFiles(test["input_files"], files)
            if "output_files" in test:
                self._collectOneGroupFiles(test["output_files"], files)
        return files

    def _collectOneGroupFiles(self, group, files):
        if isinstance(group, list):
            for f in group:
                self._collectOneFile(f, files)
        elif isinstance(group, dict):
            for name in group:
                f_or_list = group[name]
                if isinstance(f_or_list, list):
                    for f in f_or_list:
                        self._collectOneFile(f, files)
                else:
                    self._collectOneFile(f_or_list, files)

    def _collectOneFile(self, item, files):
        assert "filename" in item, "field filename must exist"
        if "location" not in item:
            return
        files.append(item)

    def _updateOneFile(self, field, model_dir, filename):
        cached_filename = \
            self._getDestFilename(field, model_dir)
        if not os.path.isfile(cached_filename) or \
                self._calculateMD5(cached_filename) != field["md5"]:
            return self._copyFile(field, cached_filename, filename)
        return False

    def _calculateMD5(self, model_name):
        m = hashlib.md5()
        m.update(open(model_name, 'rb').read())
        md5 = m.hexdigest()
        return md5

    def _copyFile(self, field, destination_name, source):
        if "location" not in field:
            return False
        location = field["location"]
        if location[0:4] == "http":
            getLogger().info("Downloading {}".format(location))
            r = requests.get(location)
            if r.status_code == 200:
                with open(destination_name, 'wb') as f:
                    f.write(r.content)
        else:
            abs_name = self._getAbsFilename(field, source, None)
            shutil.copyfile(abs_name, destination_name)
        assert os.path.isfile(destination_name), \
            "File {} cannot be retrieved".format(destination_name)
        # verify the md5 matches the file downloaded
        md5 = self._calculateMD5(destination_name)
        if md5 != field["md5"]:
            getLogger().info("Source file {} is changed, ".format(location) +
                             " updating MD5. " +
                             "Please commit the updated json file.")
            field["md5"] = md5
            return True
        return False

    def _getDestFilename(self, field, dir):
        fn = os.path.splitext(field["filename"])
        cached_name = dir + "/" + fn[0] + fn[1]
        return cached_name

    def _updateTests(self, one_benchmark, source):
        if one_benchmark["tests"][0]["metric"] == "generic":
            return

        # framework specific updates
        self.framework.rewriteBenchmarkTests(one_benchmark, source)

        # Update identifiers, the last update
        self._updateNewTestFields(one_benchmark["tests"], one_benchmark)

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
                deepMerge(test["commands"], one_benchmark["model"]["commands"])

    def _getAbsFilename(self, file, source, cache_dir):
        location = file["location"]
        filename = file["filename"]
        if location[0:4] == "http":
            # Need to download, return the destination filename
            return cache_dir + "/" + filename
        elif location[0:2] == "//":
            assert getArgs().root_model_dir is not None, \
                "When specifying relative directory, the " \
                "--root_model_dir must be specified."
            return getArgs().root_model_dir + location[1:]
        elif location[0] != "/":
            abs_dir = os.path.dirname(os.path.abspath(source)) + "/"
            return abs_dir + location
        else:
            return location
