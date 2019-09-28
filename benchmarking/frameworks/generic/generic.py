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
import os
from frameworks.framework_base import FrameworkBase


class GenericFramework(FrameworkBase):
    def __init__(self, tempdir, args):
        super(GenericFramework, self).__init__(args)
        self.tempdir = os.path.join(tempdir, self.getName())
        os.makedirs(self.tempdir, 0o777)

    def getName(self):
        return "generic"

    def runOnPlatform(self, total_num, cmd, platform, platform_args,
                      converter):
        _, meta = platform.runBenchmark(cmd, platform_args=platform_args)
        results = {}
        results["meta"] = meta
        return results
