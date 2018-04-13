#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from utils.arg_parse import getArgs
from .local_reporter.local_reporter import LocalReporter
from .remote_reporter.remote_reporter import RemoteReporter
from .simple_local_reporter.simple_local_reporter import SimpleLocalReporter
from .screen_reporter.screen_reporter import ScreenReporter


def getReporters():
    reporters = []
    if getArgs().local_reporter:
        reporters.append(LocalReporter())
    if getArgs().simple_local_reporter:
        reporters.append(SimpleLocalReporter())
    if getArgs().remote_reporter:
        reporters.append(RemoteReporter())
    if getArgs().screen_reporter:
        reporters.append(ScreenReporter())
    return reporters
