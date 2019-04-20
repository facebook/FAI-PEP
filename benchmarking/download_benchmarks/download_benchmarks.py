#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals
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
        if not os.path.isdir(self.root_model_dir):
            os.makedirs(self.root_model_dir)

        for benchmark in benchmarks:
            self._processOneBenchmark(benchmark)

    def _processOneBenchmark(self, benchmark):
        filename = benchmark["filename"]
        one_benchmark = benchmark["content"]

        # TODO refactor the code to collect files
        if "model" in one_benchmark:
            if "files" in one_benchmark["model"]:
                for field in one_benchmark["model"]["files"]:
                    value = one_benchmark["model"]["files"][field]
                    assert "location" in value, \
                        "location field is missing in benchmark " \
                        "{}".format(filename)
                    location = value["location"]
                    md5 = value.get("md5")
                    self.downloadFile(location, md5)
            if "libraries" in one_benchmark["model"]:
                for value in one_benchmark["model"]["libraries"]:
                    assert "location" in value, \
                        "location field is missing in benchmark " \
                        "{}".format(filename)
                    location = value["location"]
                    md5 = value["md5"]
                    self.downloadFile(location, md5)

        assert "tests" in one_benchmark, \
            "tests field is missing in benchmark {}".format(filename)
        tests = one_benchmark["tests"]
        for test in tests:
            if "input_files" in test:
                self._downloadTestFiles(test["input_files"])
            if "output_files" in test:
                self._downloadTestFiles(test["output_files"])
            if "preprocess" in test and "files" in test["preprocess"]:
                self._downloadTestFiles(test["preprocess"]["files"])
            if "postprocess" in test and "files" in test["postprocess"]:
                self._downloadTestFiles(test["postprocess"]["files"])

    def downloadFile(self, location, md5):
        if location[0:2] != "//":
            return
        else:
            dirs = location[2:].split("/")
            if len(dirs) <= 2:
                return
            path = self.root_model_dir + location[1:]
        if os.path.isfile(path):
            if md5:
                m = hashlib.md5()
                m.update(open(path, 'rb').read())
                new_md5 = m.hexdigest()
                if md5 == new_md5:
                    getLogger().info("File {}".format(os.path.basename(path)) +
                        " is cached, skip downloading")
                    return
            else:
                # assume the file is the same
                return
        downloader_controller = DownloadFile(dirs=dirs,
                                             logger=self.logger,
                                             args=self.args)
        downloader_controller.download_file(location, path)

    def _downloadTestFiles(self, files):
        if isinstance(files, list):
            for f in files:
                if "location" in f:
                    self.downloadFile(f["location"], None)
        elif isinstance(files, dict):
            for f in files:
                value = files[f]
                if isinstance(value, list):
                    for v in value:
                        if "location" in v:
                            self.downloadFile(v["location"], None)
                else:
                    if "location" in value:
                        self.downloadFile(value["location"], None)
