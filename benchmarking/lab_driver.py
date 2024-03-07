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

import argparse
import json
import os

from download_benchmarks.download_benchmarks import DownloadBenchmarks
from harness import BenchmarkDriver
from repo_driver import RepoDriver as OSS_RepoDriver
from run_lab import RunLab
from run_remote import RunRemote
from utils.custom_logger import getLogger, setLoggerLevel
from utils.log_utils import DEFAULT_INTERVAL as default_interval, valid_interval

parser = argparse.ArgumentParser(description="Download models from dewey")
parser.add_argument(
    "--app_id", help="The app id you use to upload/download your file for everstore"
)
parser.add_argument(
    "-b",
    "--benchmark_file",
    help="Specify the json file for the benchmark or a number of benchmarks",
)
parser.add_argument(
    "--lab", action="store_true", help="Indicate whether the run is lab run."
)
parser.add_argument(
    "--logger_level",
    default="info",
    choices=["info", "warning", "error"],
    help="Specify the logger level",
)
parser.add_argument(
    "--rt_logging", action="store_true", help="Enable realtime logging to database."
)
parser.add_argument(
    "--rt_logging_interval",
    type=valid_interval,
    default=str(default_interval),
    help="Realtime logging Update interval in seconds. Minimum 5 seconds.",
)
parser.add_argument(
    "--remote",
    action="store_true",
    help="Submit the job to remote devices to run the benchmark.",
)
parser.add_argument(
    "--root_model_dir",
    required=True,
    help="The root model directory if the meta data of the model uses "
    "relative directory, i.e. the location field starts with //",
)
parser.add_argument(
    "--token", help="The token you use to upload/download your file for everstore"
)
parser.add_argument(
    "-c", "--custom_binary", help="Specify the custom binary that you want to run."
)
parser.add_argument(
    "--pre_built_binary",
    help="Specify the pre_built_binary to bypass the building process.",
)
parser.add_argument(
    "--user_string",
    help="If set, use this instead of the $USER env variable as the user string.",
)
parser.add_argument(
    "--buck_target", default="", help="The buck command to build the custom binary"
)


class LabDriver:
    def __init__(self, raw_args=None):
        self.args, self.unknowns = parser.parse_known_args(raw_args)
        setLoggerLevel(self.args.logger_level)

    def run(self):
        if (
            not self.args.lab
            and not self.args.remote
            and not "--adhoc" not in self.args
        ):
            assert self.args.benchmark_file, "--benchmark_file (-b) must be specified"

        if self.args.benchmark_file and not self.args.remote:
            getLogger().info("Checking benchmark files to download")
            dbench = DownloadBenchmarks(self.args, getLogger())
            dbench.run(self.args.benchmark_file)

        if self.args.remote:
            unique_args = [
                "--app_id",
                self.args.app_id,
                "--token",
                self.args.token,
            ]
            if self.args.benchmark_file:
                unique_args.extend(
                    [
                        "--benchmark_file",
                        self.args.benchmark_file,
                    ]
                )
            if self.args.pre_built_binary:
                unique_args.extend(
                    [
                        "--pre_built_binary",
                        self.args.pre_built_binary,
                    ]
                )
            if self.args.user_string:
                unique_args.extend(
                    [
                        "--user_string",
                        self.args.user_string,
                    ]
                )
            if self.args.buck_target:
                unique_args.extend(
                    [
                        "--buck_target",
                        self.args.buck_target,
                    ]
                )

            # hack to remove --repo from the argument list since python2
            # argparse doesn't support allow_abbrev to be False, and it is
            # the prefix of --repo_dir
            if "--repo" in self.unknowns:
                index = self.unknowns.index("--repo")
                new_unknowns = self.unknowns[:index]
                new_unknowns.extend(self.unknowns[index + 2 :])
                self.unknowns = new_unknowns
            app_class = RunRemote
        elif self.args.lab:
            unique_args = [
                "--app_id",
                self.args.app_id,
                "--token",
                self.args.token,
            ]
            if self.args.rt_logging:
                unique_args.extend(
                    [
                        "--rt_logging",
                        "--rt_logging_interval",
                        str(self.args.rt_logging_interval),
                    ]
                )
            app_class = RunLab
        elif self.args.custom_binary or self.args.pre_built_binary:
            if self.args.custom_binary:
                binary = self.args.custom_binary
            else:
                binary = self.args.pre_built_binary
            repo_info = {
                "treatment": {"program": binary, "commit": "-1", "commit_time": 0}
            }
            unique_args = [
                "--info '",
                json.dumps(repo_info) + "'",
                "--benchmark_file",
                self.args.benchmark_file,
            ]
            app_class = BenchmarkDriver
        else:
            if self.args.user_string:
                usr_string = self.args.user_string
            else:
                usr_string = os.environ["USER"]
            unique_args = [
                "--benchmark_file",
                self.args.benchmark_file,
                "--user_string",
                usr_string,
            ]
            app_class = OSS_RepoDriver

        raw_args = []
        raw_args.extend(unique_args)
        raw_args.extend(["--root_model_dir", self.args.root_model_dir])
        raw_args.extend(["--logger_level", self.args.logger_level])
        raw_args.extend(self.unknowns)
        getLogger().info("Running {} with raw_args {}".format(app_class, raw_args))
        app = app_class(raw_args=raw_args)
        res = app.run()
        if res:
            return res


if __name__ == "__main__":
    raw_args = None
    app = LabDriver(raw_args=raw_args)
    app.run()
