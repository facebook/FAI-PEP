#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from reporters.reporter_base import ReporterBase
from utils.custom_logger import getLogger

import copy
import datetime


class ScreenReporter(ReporterBase):
    def __init__(self):
        super(ScreenReporter, self).__init__()

    def report(self, content):
        data = copy.deepcopy(content[self.DATA])
        if data is None or len(data) == 0:
            getLogger().info("No data to write")
            return
        meta = content[self.META]
        net_name = meta['net_name']
        platform_name = meta[self.PLATFORM]
        framework_name = meta["framework"]
        metric_name = meta['metric']
        ts = float(meta['commit_time'])
        commit = meta['commit']

        print("NET: {}\tMETRIC: {}\tID: {}".format(net_name, metric_name,
                                                   meta["identifier"]))
        if "platform_hash" in meta:
            print("PLATFORM: {}\tHASH: {}".format(platform_name,
                                                  meta["platform_hash"]))
        else:
            print("PLATFORM: {}".format(platform_name))
        print("FRAMEWORK: {}\tCOMMIT: {}\tTIME: {}".
              format(framework_name, commit, datetime.datetime.fromtimestamp(
                     int(ts)).strftime('%Y-%m-%d %H:%M:%S')))

        for key in sorted(data):
            if "NET_DELAY" == key:
                continue
            self._printOneData(key, data[key])

        # Print NET_DELAY last
        if "NET_DELAY" in data:
            self._printOneData("NET_DELAY", data["NET_DELAY"])

    def _printOneData(self, key, d):
        print("{}: ".format(key))
        if "summary" in d:
            s = d["summary"]
            print("  value: p0: {0:.2f}  ".format(s["p0"]) +
                  "p10: {0:.2f}  ".format(s["p10"]) +
                  "p50: {0:.2f}  ".format(s["p50"]) +
                  "p90: {0:.2f}  ".format(s["p90"]) +
                  "p100: {0:.2f}".format(s["p100"]))
        if "diff_summary" in d:
            s = d["diff_summary"]
            print("  diff:  p0: {0:.2f}  ".format(s["p0"]) +
                  "p10: {0:.2f}  ".format(s["p10"]) +
                  "p50: {0:.2f}  ".format(s["p50"]) +
                  "p90: {0:.2f}  ".format(s["p90"]) +
                  "p100: {0:.2f}".format(s["p100"]))
