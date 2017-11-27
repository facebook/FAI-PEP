#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from utils.arg_parse import getArgs
from reporters.local_reporter.local_reporter import LocalReporter
from reporters.remote_reporter.remote_reporter import RemoteReporter

def getReporters():
    reporters = []
    if getArgs().local_reporter:
        reporters.append(LocalReporter())
    if getArgs().remote_reporter:
        reporters.append(RemoteReporter())
    return reporters
