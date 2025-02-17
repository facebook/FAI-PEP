#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


import copy
import datetime

from reporters.reporter_base import ReporterBase
from utils.custom_logger import getLogger


class ScreenReporter(ReporterBase):
    def __init__(self):
        super().__init__()

    def report(self, content):
        data = copy.deepcopy(content[self.DATA])
        if data is None or len(data) == 0:
            getLogger().info("No data to write")
            return
        meta = content[self.META]
        net_name = meta["net_name"]
        platform_name = meta[self.PLATFORM]
        framework_name = meta["framework"]
        metric_name = meta["metric"]
        ts = float(meta["commit_time"])
        commit = meta["commit"]

        print(
            "NET: {}\tMETRIC: {}\tID: {}".format(
                net_name, metric_name, meta["identifier"]
            )
        )
        if "platform_hash" in meta:
            print("PLATFORM: {}\tHASH: {}".format(platform_name, meta["platform_hash"]))
        else:
            print(f"PLATFORM: {platform_name}")
        print(
            "FRAMEWORK: {}\tCOMMIT: {}\tTIME: {}".format(
                framework_name,
                commit,
                datetime.datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S"),
            )
        )

        del_keys = []
        for key in data:
            if key.startswith("NET"):
                self._printOneData(key, data[key])
                del_keys.append(key)
        for key in del_keys:
            data.pop(key)

        for key in sorted(data):
            self._printOneData(key, data[key])

    def _printOneData(self, key, d):
        if "summary" in d:
            s = d["summary"]
            self._printOneDataLine(key, s)
        if "diff_summary" in d:
            s = d["diff_summary"]
            self._printOneDataLine(key, s)

    def _printOneDataLine(self, key, s):
        if "p50" in s and "MAD" in s:
            print(
                "{}: value median {:.5f}  MAD: {:.5f}".format(key, s["p50"], s["MAD"])
            )
        elif "mean" in s and "stdev" in s:
            print(
                "{}: value mean {:.5f}  stdev: {:.5f}".format(
                    key, s["mean"], s["stdev"]
                )
            )

    def _getOperatorStats(self, data):
        pass
