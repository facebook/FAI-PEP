#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import os

from utils.arg_parse import getParser, getArgs, parseKnown
from utils.build_program import buildProgramPlatform


getParser().add_argument("--dst", required=True,
    help="The destination of the program.")
getParser().add_argument("--framework", required=True,
    choices=["caffe2"],
    help="Specify the framework to benchmark on.")
getParser().add_argument("--frameworks_dir",
    default=str(os.path.dirname(os.path.realpath(__file__)) + "/../specifications/frameworks"),
    help="Required. The root directory that all frameworks resides. "
    "Usually it is the specifications/frameworks directory.")
getParser().add_argument("--platform", required=True,
    help="Specify the platform to benchmark on."
    "Use this flag if the framework"
    " needs special compilation scripts. The scripts are called build.sh "
    "saved in specifications/frameworks/<framework>/<platforms> directory")
getParser().add_argument("--repo_dir", required=True,
    help="Required. The base framework repo directory used for benchmark.")


class BuildProgram(object):
    def __init__(self):
        parseKnown()

    def run(self):
        buildProgramPlatform(getArgs().dst,
                             getArgs().repo_dir,
                             getArgs().framework,
                             getArgs().frameworks_dir,
                             getArgs().platform)


if __name__ == "__main__":
    app = BuildProgram()
    app.run()
