#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from reporters.reporter_base import ReporterBase


class SimpleScreenReporter(ReporterBase):
    def __init__(self):
        super(SimpleScreenReporter, self).__init__()

    def report(self, content):
        print(content["data"])
