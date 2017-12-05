#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import threading

from platforms.platforms import getPlatforms
from reporters.reporters import getReporters
from utils.arg_parse import getParser, parse

getParser().add_argument("--excluded_platforms",
    help="Specify the platforms that skip the test, in a comma separated list. "
    "For android devices, the specified value is the output of the command: "
    "\"adb shell getprop ro.product.model\". For host, the specified value is "
    "The output of python method: \"platform.processor()\".")
getParser().add_argument("--golden_output_file",
    help="The reference output file that contains the serialized protobuf for "
    "the output blobs. If multiple output needed, use comma "
    "separated string. Must have the same number of items as output does. "
    "The specifying order must be the same. ")
getParser().add_argument("--identifier",
    help="A unique identifier to identify this type of run so that it can be "
    "filtered out from all other regression runs in the database.")
getParser().add_argument("--info",
    help="The json serialized options describing the control and treatment.")
getParser().add_argument("--init_net", required=True,
    help="The given net to initialize any parameters.")
getParser().add_argument("--input",
    help="Input that is needed for running the network. "
    "If multiple input needed, use comma separated string.")
getParser().add_argument("--input_dims",
    help="Alternate to input_files, if all inputs are simple "
    "float TensorCPUs, specify the dimension using comma "
    "separated numbers. If multiple input needed, use "
    "semicolon to separate the dimension of different "
    "tensors.")
getParser().add_argument("--input_file",
    help="Input file that contain the serialized protobuf for "
    "the input blobs. If multiple input needed, use comma "
    "separated string. Must have the same number of items "
    "as input does.")
getParser().add_argument("--input_type",
    help="Type for the input blob. The supported options are:"
    "float, uint8_t. The default is float.")
getParser().add_argument("--iter", default=10, type=int,
    help="The number of iterations to run.")
getParser().add_argument("--metric", default="delay",
    choices=["delay", "error"],
    help="The metric to collect in this test run. The allowed values are: "
    "\"delay\": the net and operator delay. \"error\": "
    "the error in the output blobs between control and treatment.")
getParser().add_argument("--net", required=True,
    help="The given predict net to benchmark.")
getParser().add_argument("--output",
    help="Output that should be dumped after the execution "
    "finishes. If multiple outputs are needed, use comma "
    "separated string. ")
getParser().add_argument("--output_folder",
    help="The folder that the output should be written to. This "
    "folder must already exist in the file system.")
getParser().add_argument("--program",
    help="The program to run on the platform.")
getParser().add_argument("--regression_direction", type=int, default=1,
    help="The direction when regression happens. 1 means higher value is "
    "regression. -1 means lower value is regression.")
getParser().add_argument("--run_individual", action="store_true",
    help="Whether to benchmark individual operators.")
getParser().add_argument("--temp_dir",
    help="The temporary directory used by the script.")
getParser().add_argument("--timeout", default=300, type=float,
    help="Specify a timeout running the test on the platforms. "
    "The timeout value needs to be large enough so that the low end devices "
    "can safely finish the execution in normal conditions. Note, in A/B "
    "testing mode, the test runs twice. ")
getParser().add_argument("--warmup", default=0, type=int,
    help="The number of iterations to warm up.")

class BenchmarkDriver(object):
    def __init__(self):
        parse()

    def runBenchmark(self, platform):
        reporters = getReporters()
        output = platform.runOnPlatform()
        for reporter in reporters:
            reporter.report(output)

    def run(self):
        platforms = getPlatforms()
        threads = []
        for platform in platforms:
            t = threading.Thread(target=self.runBenchmark, args=(platform,))
            threads.append(t)
            t.start()

if __name__ == "__main__":
    app = BenchmarkDriver()
    app.run()
