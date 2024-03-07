#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

from frameworks.caffe2.caffe2 import Caffe2Framework
from utils.custom_logger import getLogger


class PytorchFramework(Caffe2Framework):
    IDENTIFIER = "PyTorchObserver "
    NET = "NET"

    def getName(self):
        return "pytorch"

    def runOnPlatform(self, total_num, cmd, platform, platform_args, converter):
        if converter is None:
            converter = {
                "name": "json_with_identifier_converter",
                "args": {"identifier": self.IDENTIFIER},
            }

        converter_obj = self.converters[converter["name"]]()
        args = converter.get("args")
        results = []
        num = 0

        # emulate do...while... loop
        while True:
            output, meta = platform.runBenchmark(cmd, platform_args=platform_args)
            one_result, valid_run_idxs = converter_obj.collect(output, args)
            valid_run_idxs = [num + idx for idx in valid_run_idxs]
            num += len(valid_run_idxs)
            results.extend(one_result)
            if num < total_num:
                num_items = len(valid_run_idxs)
                if num_items > 0:
                    getLogger().info(
                        "%d items collected, Still missing %d "
                        "runs. Collect again." % (num_items, total_num - num)
                    )

                    continue
                else:
                    getLogger().info("No new items collected, " "finish collecting...")
            elif total_num >= 0 and num > total_num:
                # if collect more than the needed number, get the
                # latest entries. This may happen when the data in
                # the previous runs are not cleared. e.g. on some
                # android 5 devices. Or, it may happen when multiple
                # runs are needed to collect the desired number of
                # iterations
                results = results[valid_run_idxs[num - total_num] :]
            break
        metric = converter_obj.convert(results)
        metric["meta"] = meta
        return metric
