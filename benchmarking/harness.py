#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import argparse
import copy
import json
import os
import shutil
import sys
import tempfile
import threading
import time

from driver.benchmark_driver import runOneBenchmark
from benchmarks.benchmarks import BenchmarkCollector
from frameworks.frameworks import getFrameworks
from platforms.platforms import getPlatforms
from reporters.reporters import getReporters
from utils.custom_logger import getLogger
from utils.utilities import parse_kwarg, getRunStatus, setRunStatus

parser = argparse.ArgumentParser()
parser.add_argument("--android_dir", default="/data/local/tmp/",
    help="The directory in the android device all files are pushed to.")
# for backward compatible purpose
parser.add_argument("--backend",
    help="Specify the backend the test runs on.")
parser.add_argument("-b", "--benchmark_file", required=True,
    help="Specify the json file for the benchmark or a number of benchmarks")
parser.add_argument("--command_args",
    help="Specify optional command arguments that would go with the "
    "main benchmark command")
parser.add_argument("--cooldown", default=0, type=float,
    help = "Specify the time interval between two test runs.")
parser.add_argument("--debug", action="store_true",
    help="Debug mode to retain all the running binaries and models.")
parser.add_argument("--device",
    help="The single device to run this benchmark on")
parser.add_argument("-d", "--devices",
    help="Specify the devices to run the benchmark, in a comma separated "
    "list. The value is the device or device_hash field of the meta info.")
parser.add_argument("--env", help="environment variables passed to runtime binary.",
    nargs="*", type=parse_kwarg, default=[])
parser.add_argument("--excluded_devices",
    help="Specify the devices that skip the benchmark, in a comma separated "
    "list. The value is the device or device_hash field of the meta info.")
parser.add_argument("--framework", required=True,
    choices=["caffe2", "generic", "oculus", "pytorch", "tflite", "glow"],
    help="Specify the framework to benchmark on.")
parser.add_argument("--info", required=True,
    help="The json serialized options describing the control and treatment.")
parser.add_argument("--ios_dir", default="/tmp",
    help="The directory in the ios device all files are pushed to.")
parser.add_argument("--local_reporter",
    help="Save the result to a directory specified by this argument.")
parser.add_argument("--monsoon_map",
    help="Map the phone hash to the monsoon serial number.")
parser.add_argument("--simple_local_reporter",
    help="Same as local reporter, but the directory hierarchy is reduced.")
parser.add_argument("--model_cache", required=True,
    help="The local directory containing the cached models. It should not "
    "be part of a git directory.")
parser.add_argument("-p", "--platform", required=True,
    help="Specify the platform to benchmark on. Use this flag if the framework"
    " needs special compilation scripts. The scripts are called build.sh "
    "saved in " + os.path.join("specifications",
    "frameworks", "<framework>", "<platform>") + " directory")
parser.add_argument("--platform_sig",
    help="Specify the platform signature")
parser.add_argument("--program",
    help="The program to run on the platform.")
parser.add_argument("--reboot", action="store_true",
    help="Tries to reboot the devices before launching benchmarks for one "
    "commit.")
parser.add_argument("--regressed_types",
    help="A json string that encodes the types of the regressed tests.")
parser.add_argument("--remote_reporter",
    help="Save the result to a remote server. "
    "The style is <domain_name>/<endpoint>|<category>")
parser.add_argument("--remote_access_token",
    help="The access token to access the remote server")
parser.add_argument("--root_model_dir",
    help="The root model directory if the meta data of the model uses "
    "relative directory, i.e. the location field starts with //")
parser.add_argument("--run_type", default="benchmark",
    choices=["benchmark", "verify", "regress"],
    help="The type of the current run. The allowed values are: "
    "benchmark, the normal benchmark run."
    "verify, the benchmark is re-run to confirm a suspicious regression."
    "regress, the regression is confirmed.")
parser.add_argument("--screen_reporter", action="store_true",
    help="Display the summary of the benchmark result on screen.")
parser.add_argument("--simple_screen_reporter", action="store_true",
    help="Display the result on screen with no post processing.")
parser.add_argument("--set_freq",
    help="On rooted android phones, set the frequency of the cores. "
    "The supported values are: "
    "max: set all cores to the maximum frquency. "
    "min: set all cores to the minimum frequency. "
    "mid: set all cores to the median frequency. ")
parser.add_argument("--shared_libs",
    help="Pass the shared libs that the framework depends on, "
    "in a comma separated list.")
parser.add_argument("--string_map",
    help="A json string mapping tokens to replacement strings. "
    "The tokens, surrended by {}, when appearing in the test fields of "
    "the json file, are to be replaced with the mapped values.")
parser.add_argument("--timeout", default=300, type=float,
    help="Specify a timeout running the test on the platforms. "
    "The timeout value needs to be large enough so that the low end devices "
    "can safely finish the execution in normal conditions. ")
parser.add_argument("--user_identifier",
    help="User can specify an identifier and that will be passed to the "
    "output so that the result can be easily identified.")
# for backward compabile purpose
parser.add_argument("--wipe_cache", default=False,
    help="Specify whether to evict cache or not before running")
parser.add_argument("--hash_platform_mapping",
    help="Specify the devices hash platform mapping json file.")
# Avoid the prefix user so that it doesn't collide with --user_identifier
parser.add_argument("--user_string",
    help="Specify the user running the test (to be passed to the remote reporter).")


class BenchmarkDriver(object):
    def __init__(self, **kwargs):
        setRunStatus(0, overwrite=True)
        self.status = 0
        raw_args = kwargs.get("raw_args", None)
        self.args, self.unknowns = parser.parse_known_args(raw_args)
        self._lock = threading.Lock()

    def runBenchmark(self, info, platform, benchmarks):
        if self.args.reboot:
            platform.rebootDevice()
        for idx in range(len(benchmarks)):
            tempdir = tempfile.mkdtemp()
            # we need to get a different framework instance per thread
            # will consolidate later. For now create a new framework
            frameworks = getFrameworks()
            framework = frameworks[self.args.framework](tempdir, self.args)
            reporters = getReporters(self.args)

            benchmark = benchmarks[idx]
            # check the framework matches
            if "model" in benchmark and "framework" in benchmark["model"]:
                assert(benchmark["model"]["framework"] == self.args.framework), \
                    "Framework specified in the json file " \
                    "{} ".format(benchmark["model"]["framework"]) + \
                    "does not match the command line argument " \
                    "{}".format(self.args.framework)
            if self.args.debug:
                for test in benchmark["tests"]:
                    test["log_output"] = True
            if self.args.env:
                for test in benchmark["tests"]:
                    cmd_env = dict(self.args.env)
                    if "env" in test:
                        cmd_env.update(test["env"])
                    test["env"] = cmd_env

            b = copy.deepcopy(benchmark)
            i = copy.deepcopy(info)
            status = runOneBenchmark(i, b, framework, platform,
                                     self.args.platform,
                                     reporters, self._lock,
                                     self.args.cooldown,
                                     self.args.user_identifier,
                                     self.args.local_reporter)
            self.status = self.status | status
            if idx != len(benchmarks) - 1:
                # cool down period between multiple benchmark runs
                cooldown = self.args.cooldown
                if "model" in benchmark and "cooldown" in benchmark["model"]:
                    cooldown = float(benchmark["model"]["cooldown"])
                time.sleep(cooldown)
            if not self.args.debug:
                shutil.rmtree(tempdir, True)
                for test in benchmark["tests"]:
                    if "preprocess" in test and "files" in test["preprocess"]:
                        for f in test["preprocess"]["files"].values():
                            shutil.rmtree(f["location"], True)

    def run(self):
        tempdir = tempfile.mkdtemp()
        getLogger().info("Temp directory: {}".format(tempdir))
        info = self._getInfo()
        frameworks = getFrameworks()
        assert self.args.framework in frameworks, \
            "Framework {} is not supported".format(self.args.framework)
        framework = frameworks[self.args.framework](tempdir, self.args)
        bcollector = BenchmarkCollector(framework, self.args.model_cache,
                                        args=self.args)
        benchmarks = bcollector.collectBenchmarks(info,
                                                  self.args.benchmark_file)
        platforms = getPlatforms(tempdir, self.args)
        threads = []
        for platform in platforms:
            t = threading.Thread(target=self.runBenchmark,
                                 args=(info, platform, benchmarks))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()

        if not self.args.debug:
            shutil.rmtree(tempdir, True)

        status = self.status | getRunStatus()
        if status == 0:
            status_str = "success"
        elif status == 1:
            status_str = "user error"
        elif status == 2:
            status_str = "harness error"
        else:
            status_str = "user and harness error"
        getLogger().info(" ======= {} =======".format(status_str))
        return status

    def _getInfo(self):
        info = json.loads(self.args.info)
        info["run_type"] = "benchmark"
        if "meta" not in info:
            info["meta"] = {}
        info["meta"]["command_args"] = self.args.command_args \
            if self.args.command_args else ""

        # for backward compatible purpose
        if self.args.backend:
            info["meta"]["command_args"] += \
                " --backend {}".format(self.args.backend)
        if self.args.wipe_cache:
            info["meta"]["command_args"] += \
                " --wipe_cache {}".format(self.args.wipe_cache)
        if self.args.user_string:
            info["user"] = self.args.user_string

        return info


if __name__ == "__main__":
    app = BenchmarkDriver()
    status = app.run()
    sys.exit(status)
