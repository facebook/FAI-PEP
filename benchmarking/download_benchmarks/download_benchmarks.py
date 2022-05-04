#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import gc
import hashlib
import os

from utils.custom_logger import getLogger
from utils.utilities import getBenchmarks, getFilename

from .download_file import DownloadFile


class DownloadBenchmarks(object):
    def __init__(self, args, logger):
        self.args = args
        self.root_model_dir = self.args.root_model_dir
        self.logger = logger
        self.everstore = None
        assert self.args.root_model_dir, "root_model_dir is not set"

    def run(self, benchmark_file):
        assert benchmark_file, "benchmark_file is not set"
        benchmarks = getBenchmarks(benchmark_file)
        locations = []
        if not os.path.isdir(self.root_model_dir):
            os.makedirs(self.root_model_dir)

        for benchmark in benchmarks:
            location = self._processOneBenchmark(benchmark)
            locations.extend(location)
        locations = [l for l in locations if l]
        return locations

    def _processOneBenchmark(self, benchmark):
        filename = benchmark["filename"]
        one_benchmark = benchmark["content"]
        locations = []
        # TODO refactor the code to collect files
        if "model" in one_benchmark:
            if "files" in one_benchmark["model"]:
                for field in one_benchmark["model"]["files"]:
                    value = one_benchmark["model"]["files"][field]
                    assert (
                        "location" in value
                    ), "location field is missing in benchmark " "{}".format(filename)
                    location = value["location"]
                    md5 = value.get("md5")
                    path = self.downloadFile(location, md5)
                    locations.append(path)
            if "libraries" in one_benchmark["model"]:
                for value in one_benchmark["model"]["libraries"]:
                    assert (
                        "location" in value
                    ), "location field is missing in benchmark " "{}".format(filename)
                    location = value["location"]
                    md5 = value["md5"]
                    path = self.downloadFile(location, md5)
                    locations.append(path)

        assert (
            "tests" in one_benchmark
        ), "tests field is missing in benchmark {}".format(filename)
        tests = one_benchmark["tests"]
        for test in tests:
            if "input_files" in test:
                path = self._downloadTestFiles(test["input_files"])
                locations.extend(path)
            if "output_files" in test:
                path = self._downloadTestFiles(test["output_files"])
                locations.extend(path)
            if "preprocess" in test and "files" in test["preprocess"]:
                path = self._downloadTestFiles(test["preprocess"]["files"])
                locations.extend(path)
            if "postprocess" in test and "files" in test["postprocess"]:
                path = self._downloadTestFiles(test["postprocess"]["files"])
                locations.extend(path)

        return locations

    def downloadFile(self, location, md5):
        if location.startswith("http"):
            dirs = location.split(":/")
            replace_pattern = {
                " ": "-",
                "\\": "-",
                ":": "/",
            }
            path = os.path.join(
                self.root_model_dir,
                getFilename(location, replace_pattern=replace_pattern),
            )
        elif not location.startswith("//"):
            return
        else:
            dirs = location[2:].split("/")
            if len(dirs) <= 2:
                return
            path = self.root_model_dir + location[1:]
        if os.path.isfile(path):
            if md5:
                getLogger().info("Calculate md5 of {}".format(path))
                file_hash = None
                with open(path, "rb") as f:
                    file_hash = hashlib.md5()
                    for chunk in iter(lambda: f.read(8192), b""):
                        file_hash.update(chunk)
                new_md5 = file_hash.hexdigest()
                del file_hash
                gc.collect()
                if md5 == new_md5:
                    getLogger().info(
                        "File {}".format(os.path.basename(path))
                        + " is cached, skip downloading"
                    )
                    return path
            # If file exists, but we don't have an md5, allow each downloader to handle this.
        downloader_controller = DownloadFile(
            dirs=dirs, logger=self.logger, args=self.args
        )
        downloader_controller.download_file(location, path)
        return path

    def _downloadTestFiles(self, files):
        locations = []
        if isinstance(files, list):
            for f in files:
                if "location" in f:
                    path = self.downloadFile(f["location"], None)
                    locations.append(path)
        elif isinstance(files, dict):
            for f in files:
                value = files[f]
                if isinstance(value, list):
                    for v in value:
                        if "location" in v:
                            path = self.downloadFile(v["location"], None)
                            locations.append(path)
                else:
                    if "location" in value:
                        path = self.downloadFile(value["location"], None)
                        locations.append(path)
        return locations
