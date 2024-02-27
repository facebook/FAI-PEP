#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import copy
import gc
import hashlib
import json
import os
import shutil
import tempfile

import requests
from utils.custom_logger import getLogger
from utils.utilities import deepMerge, deepReplace


COPY_THRESHOLD = 6442450944  # 6 GB


class BenchmarkCollector:
    def __init__(self, framework, model_cache, **kwargs):

        self.args = kwargs.get("args", None)
        if not os.path.isdir(model_cache):
            os.makedirs(model_cache)
        self.model_cache = model_cache
        self.framework = framework

    def collectBenchmarks(self, info, source, user_identifier):
        assert os.path.isfile(source), "Source {} is not a file".format(source)
        with open(source, "r") as f:
            content = json.load(f)

        meta = content["meta"] if "meta" in content else {}
        if "meta" in info:
            deepMerge(meta, info["meta"])
        if hasattr(self.args, "timeout"):
            meta["timeout"] = self.args.timeout
        benchmarks = []

        if "benchmarks" in content:
            path = os.path.abspath(os.path.dirname(source))
            assert "meta" in content, "Meta field is missing in benchmarks"
            for benchmark_file in content["benchmarks"]:
                benchmark_file = os.path.join(path, benchmark_file)
                self._collectOneBenchmark(
                    benchmark_file, meta, benchmarks, info, user_identifier
                )
        else:
            self._collectOneBenchmark(source, meta, benchmarks, info, user_identifier)

        for b in benchmarks:
            self._verifyBenchmark(b, b["path"], True)
        return benchmarks

    def _verifyBenchmark(self, benchmark, filename, is_post):
        self.framework.verifyBenchmarkFile(benchmark, filename, is_post)

    def _collectOneBenchmark(self, source, meta, benchmarks, info, user_identifier):
        assert os.path.isfile(source), "Benchmark {} does not exist".format(source)
        with open(source, "r") as b:
            one_benchmark = json.load(b)

        string_map = json.loads(self.args.string_map) if self.args.string_map else {}
        for name in string_map:
            value = string_map[name]
            deepReplace(one_benchmark, "{" + name + "}", value)

        self._verifyBenchmark(one_benchmark, source, False)

        self._updateFiles(one_benchmark, source, user_identifier)

        # following change should not appear in updated_json file
        if meta:
            deepMerge(one_benchmark["model"], meta)

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
    def _updateFiles(self, one_benchmark, filename, user_identifier):

        model = one_benchmark["model"]
        model_dir = os.path.join(self.model_cache, model["format"], model["name"])
        if not os.path.isdir(model_dir):
            os.makedirs(model_dir)
        collected_files, collected_tmp_files = self._collectFiles(one_benchmark)
        update_json = False
        for file in collected_files:
            update_json |= self._updateOneFile(file, model_dir, filename)

        if update_json:
            s = json.dumps(one_benchmark, indent=2, sort_keys=True)
            with open(filename, "w") as f:
                f.write(s)
            getLogger().info(
                "Model {} is changed. ".format(model["name"])
                + "Please update the meta json file."
            )

        for file in collected_files:
            if "md5" in file:
                cached_filename = self._getDestFilename(file, model_dir)
                file["location"] = cached_filename
            elif file.get("location", "").startswith("//fbpkg"):
                file["location"] = self.args.root_model_dir + file["location"][1:]

        tmp_dir = tempfile.mkdtemp(
            prefix="_".join(["aibench", str(user_identifier), ""])
        )
        for tmp_file in collected_tmp_files:
            tmp_file["location"] = tmp_file["location"].replace("{TEMPDIR}", tmp_dir)

    def _collectFiles(self, benchmark):
        files = []
        tmp_files = []
        if "model" in benchmark:
            if "files" in benchmark["model"]:
                self._collectOneGroupFiles(benchmark["model"]["files"], files)
            if "libraries" in benchmark["model"]:
                self._collectOneGroupFiles(benchmark["model"]["libraries"], files)

        for test in benchmark["tests"]:
            if "files" in test:
                self._collectOneGroupFiles(test["files"], files, tmp_files)
            if "input_files" in test:
                self._collectOneGroupFiles(test["input_files"], files)
            if "output_files" in test:
                self._collectOneGroupFiles(test["output_files"], files, tmp_files)
            if "preprocess" in test and "files" in test["preprocess"]:
                self._collectOneGroupFiles(
                    test["preprocess"]["files"], files, tmp_files
                )
            if "postprocess" in test and "files" in test["postprocess"]:
                self._collectOneGroupFiles(
                    test["postprocess"]["files"], files, tmp_files
                )
        return files, tmp_files

    def _collectOneGroupFiles(self, group, files, tmp_files=None):
        if isinstance(group, list):
            for f in group:
                self._collectOneFile(f, files, tmp_files)
        elif isinstance(group, dict):
            for name in group:
                f_or_list = group[name]
                if isinstance(f_or_list, list):
                    for f in f_or_list:
                        self._collectOneFile(f, files, tmp_files)
                else:
                    self._collectOneFile(f_or_list, files, tmp_files)

    def _collectOneFile(self, item, files, tmp_files):
        if "location" in item and "{TEMPDIR}" in item["location"]:
            assert tmp_files is not None, "tmp file can only exist for output"
            tmp_files.append(item)
            return
        assert "filename" in item, "field filename must exist"
        if "location" not in item:
            return
        files.append(item)

    def _updateOneFile(self, field, model_dir, filename):
        cached_filename = self._getDestFilename(field, model_dir)
        if (
            "md5" in field
            and field["md5"] is not None
            and (
                not os.path.isfile(cached_filename)
                or self._calculateMD5(cached_filename, field["md5"], filename)
                != field["md5"]
            )
        ):
            return self._copyFile(field, cached_filename, filename)
        return False

    def _calcalateFileMD5(self, model_name: str) -> str:
        with open(model_name, "rb") as f:
            file_hash = hashlib.md5()
            for chunk in iter(lambda: f.read(8192), b""):
                file_hash.update(chunk)
        md5 = file_hash.hexdigest()
        del file_hash
        gc.collect()
        return md5

    def _calcalateDirMD5(self, dir_path: str) -> str:
        """
        Calculate md5 for given directory by summation all md5s of the files in that directory.
        """
        file_hashes = []
        for root, _, filenames in os.walk(dir_path):
            for filename in filenames:
                filepath = os.path.join(root, filename)
                file_hash = self._calcalateFileMD5(filepath)
                file_hashes.append(file_hash)
        return hashlib.md5("".join(file_hashes).encode("utf-8")).hexdigest()

    def _calculateMD5(self, model_name: str, old_md5: str, filename: str) -> str:
        if os.stat(filename).st_size >= COPY_THRESHOLD or os.path.islink(model_name):
            if not os.path.isfile(model_name):
                getLogger().info(
                    "Create symlink between {} and {}".format(filename, model_name)
                )
                os.symlink(filename, model_name)
            return old_md5
        getLogger().info("Calculate md5 of {}".format(model_name))
        if os.path.isdir(model_name):
            return self._calcalateDirMD5(model_name)
        elif os.path.isfile(model_name):
            return self._calcalateFileMD5(model_name)
        else:
            raise ValueError(
                f"`{model_name}` needs to be a path to a existing file or directory"
            )

    def _copyFile(self, field, destination_name, source):
        if "location" not in field:
            return False
        location = field["location"]
        if location[0:4] == "http":
            abs_name = destination_name
            getLogger().info("Downloading {}".format(location))
            r = requests.get(location)
            if r.status_code == 200:
                with open(destination_name, "wb") as f:
                    f.write(r.content)
        else:
            abs_name = self._getAbsFilename(field, source, None)
            if os.path.isfile(abs_name):
                if os.stat(abs_name).st_size < COPY_THRESHOLD:
                    shutil.copyfile(abs_name, destination_name)
                else:
                    if not os.path.isfile(destination_name):
                        getLogger().info(
                            "Create symlink between {} and {}".format(
                                abs_name, destination_name
                            )
                        )
                        os.symlink(abs_name, destination_name)
            elif os.path.isdir(abs_name):
                import distutils.dir_util

                distutils.dir_util.copy_tree(abs_name, destination_name)
            else:
                raise AssertionError(f"Path {abs_name} cannot be retrieved.")
                return False
        if os.path.isdir(destination_name) and field["md5"] == "directory":
            return False
        # verify the md5 matches the file downloaded
        md5 = self._calculateMD5(destination_name, field["md5"], abs_name)
        if md5 != field["md5"]:
            getLogger().info(
                "Source file {} is changed, ".format(location)
                + " updating MD5. "
                + "Please commit the updated json file."
            )
            field["md5"] = md5
            return True
        return False

    def _getDestFilename(self, field, dir):
        fn = os.path.splitext(field["filename"])
        cached_name = os.path.join(dir, fn[0] + fn[1])
        return cached_name

    def _updateTests(self, one_benchmark, source):
        if one_benchmark["tests"][0]["metric"] == "generic":
            return

        # framework specific updates
        self.framework.rewriteBenchmarkTests(one_benchmark, source)

        # rewrite test fields for compatibility reasons
        for test in one_benchmark["tests"]:
            self._rewriteTestFields(test)

        # Update identifiers, the last update
        self._updateNewTestFields(one_benchmark["tests"], one_benchmark)

    def _rewriteTestFields(self, test):
        if "arguments" in test:
            assert (
                "commands" not in test
            ), "Commands and arguments cannot co-exist in test"
            test["commands"] = ["{program} " + test["arguments"]]
            del test["arguments"]
        if "command" in test:
            assert (
                "commands" not in test
            ), "Commands and command cannot co-exist in test"
            test["commands"] = [test["command"]]
            # do not delete for now
            # del test["command"]

    def _updateNewTestFields(self, tests, one_benchmark):
        idx = 0
        for test in tests:
            identifier = test["identifier"].replace("{ID}", str(idx))
            test["identifier"] = identifier
            idx += 1

    def _getAbsFilename(self, file, source, cache_dir):
        location = file["location"]
        filename = file["filename"]
        if location[0:4] == "http":
            # Need to download, return the destination filename
            return os.path.join(cache_dir, filename)
        elif location[0:2] == "//":
            assert self.args.root_model_dir is not None, (
                "When specifying relative directory, the "
                "--root_model_dir must be specified."
            )
            return self.args.root_model_dir + location[1:]
        elif location[0] != "/":
            abs_dir = os.path.dirname(os.path.abspath(source))
            return os.path.join(abs_dir, location)
        else:
            return location
