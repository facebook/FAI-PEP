#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


from .local_reporter.local_reporter import LocalReporter
from .remote_reporter.remote_reporter import RemoteReporter
from .screen_reporter.screen_reporter import ScreenReporter
from .simple_local_reporter.simple_local_reporter import SimpleLocalReporter
from .simple_screen_reporter.simple_screen_reporter import SimpleScreenReporter


def getReporters(args):
    reporters = []
    if args.local_reporter:
        reporters.append(LocalReporter(args.local_reporter))
    if args.simple_local_reporter:
        reporters.append(SimpleLocalReporter(args.simple_local_reporter))
    if args.remote_reporter:
        reporters.append(RemoteReporter(args.remote_reporter, args.remote_access_token))
    if args.screen_reporter:
        reporters.append(ScreenReporter())
    if args.simple_screen_reporter:
        reporters.append(SimpleScreenReporter())
    return reporters
