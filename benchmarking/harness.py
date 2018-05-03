#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import copy
import json
import shutil
import tempfile
import threading

from driver.benchmark_driver import runOneBenchmark
from benchmarks.benchmarks import BenchmarkCollector
from frameworks.frameworks import getFrameworks
from platforms.platforms import getPlatforms
from reporters.reporters import getReporters
from utils.arg_parse import getParser, getArgs, parseKnown
from utils.custom_logger import getLogger

getParser().add_argument("--backend",
    help="Specify the backend the test runs on.")
getParser().add_argument("-b", "--benchmark_file", required=True,
    help="Specify the json file for the benchmark or a number of benchmarks")
getParser().add_argument("-d", "--devices",
    help="Specify the devices to run the benchmark, in a comma separated "
    "list. The value is the device or device_hash field of the meta info.")
getParser().add_argument("--excluded_devices",
    help="Specify the devices that skip the benchmark, in a comma separated "
    "list. The value is the device or device_hash field of the meta info.")
getParser().add_argument("--framework", required=True,
    choices=["caffe2"],
    help="Specify the framework to benchmark on.")
getParser().add_argument("--info", required=True,
    help="The json serialized options describing the control and treatment.")
getParser().add_argument("--local_reporter",
    help="Save the result to a directory specified by this argument.")
getParser().add_argument("--simple_local_reporter",
    help="Same as local reporter, but the directory hierarchy is reduced.")
getParser().add_argument("--model_cache", required=True,
    help="The local directory containing the cached models. It should not "
    "be part of a git directory.")
getParser().add_argument("--device",
    help="The single device to run this benchmark on")
getParser().add_argument("-p", "--platform", required=True,
    help="Specify the platform to benchmark on. Use this flag if the framework"
    " needs special compilation scripts. The scripts are called build.sh "
    "saved in specifications/frameworks/<framework>/<platform> directory")
getParser().add_argument("--program",
    help="The program to run on the platform.")
getParser().add_argument("--reboot", action="store_true",
    help="Tries to reboot the devices before launching benchmarks for one "
    "commit.")
getParser().add_argument("--regressed_types",
    help="A json string that encodes the types of the regressed tests.")
getParser().add_argument("--remote_reporter",
    help="Save the result to a remote server. "
    "The style is <domain_name>/<endpoint>|<category>")
getParser().add_argument("--remote_access_token",
    help="The access token to access the remote server")
getParser().add_argument("--root_model_dir",
    help="The root model directory if the meta data of the model uses "
    "relative directory, i.e. the location field starts with //")
getParser().add_argument("--run_type", default="benchmark",
    choices=["benchmark", "verify", "regress"],
    help="The type of the current run. The allowed values are: benchmark, the "
    "normal benchmark run. verify, the benchmark is re-run to confirm a "
    "suspicious regression. regress, the regression is confirmed.")
getParser().add_argument("--screen_reporter", action="store_true",
    help="Display the summary of the benchmark result on screen.")
getParser().add_argument("--set_freq",
    help="On rooted android phones, set the frequency of the cores. "
    "The supported values are: "
    "max: set all cores to the maximum frquency. "
    "min: set all cores to the minimum frequency. "
    "mid: set all cores to the median frequency. ")
getParser().add_argument("--shared_libs",
    help="Pass the shared libs that the framework depends on, "
    "in a comma separated list.")
getParser().add_argument("--timeout", default=300, type=float,
    help="Specify a timeout running the test on the platforms. "
    "The timeout value needs to be large enough so that the low end devices "
    "can safely finish the execution in normal conditions. Note, in A/B "
    "testing mode, the test runs twice. ")
getParser().add_argument("--user_identifier",
    help="User can specify an identifier and that will be passed to the "
    "output so that the result can be easily identified.")


class BenchmarkDriver(object):
    def __init__(self):
        parseKnown()

    def runBenchmark(self, info, platform, benchmarks, framework):
        if getArgs().reboot:
            platform.rebootDevice()
        reporters = getReporters()
        for benchmark in benchmarks:
            b = copy.deepcopy(benchmark)
            i = copy.deepcopy(info)
            runOneBenchmark(i, b, framework, platform, getArgs().platform,
                            reporters)

    def run(self):
        tempdir = tempfile.mkdtemp()
        getLogger().info("Temp directory: {}".format(tempdir))
        info = self._getInfo()
        bcollector = BenchmarkCollector(getArgs().model_cache)
        benchmarks = bcollector.collectBenchmarks(info,
                                                  getArgs().benchmark_file)
        frameworks = getFrameworks()
        assert getArgs().framework in frameworks, \
            "Framework {} is not supported".format(getArgs().framework)
        framework = frameworks[getArgs().framework](tempdir)
        platforms = getPlatforms(tempdir)
        threads = []
        for platform in platforms:
            t = threading.Thread(target=self.runBenchmark,
                                 args=(info, platform, benchmarks, framework))
            threads.append(t)
            t.start()
        shutil.rmtree(tempdir, True)

    def _getInfo(self):
        info = json.loads(getArgs().info)
        info["run_type"] = "benchmark"
        if getArgs().backend:
            info["commands"] = {}
            info["commands"][getArgs().framework] = {
                "backend": getArgs().backend
            }
        return info


if __name__ == "__main__":
    app = BenchmarkDriver()
    app.run()
