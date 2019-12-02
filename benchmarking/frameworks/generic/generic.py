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
    IDENTIFIER = 'PyTorchObserver '

    def __init__(self, tempdir, args):
        super(GenericFramework, self).__init__(args)
        self.tempdir = os.path.join(tempdir, self.getName())
        os.makedirs(self.tempdir, 0o777)

    def getName(self):
        return "generic"

    def runOnPlatform(self, total_num, cmd, platform, platform_args,
                      converter):
        if converter is None:
            converter = {
                "name": "json_with_identifier_converter",
                "args": {
                    "identifier": self.IDENTIFIER
                }
            }

        converter_obj = self.converters[converter["name"]]()
        args = converter.get("args")
        results = []
        output, meta = platform.runBenchmark(cmd, platform_args=platform_args)
        one_result, valid_run_idxs = converter_obj.collect(output, args)
        results.extend(one_result)
        metric = converter_obj.convert(results)
        metric["meta"] = meta

        return metric
