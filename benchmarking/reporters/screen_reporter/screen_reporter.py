#!/usr/bin/env python

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

        del_keys = []
        for key in data:
            if key.startswith('NET'):
                self._printOneData(key, data[key])
                del_keys.append(key)
        for key in del_keys:
            data.pop(key)

        data_values_iter = iter(data.values())
        if "id" in next(data_values_iter):
            # Print per layer delay in order
            for key in sorted(data, key=lambda x: int(data[x]["id"][0])):
                self._printOneData(key, data[key])
        else:
            for key in sorted(data):
                self._printOneData(key, data[key])


    def _printOneData(self, key, d):
        if "summary" in d:
            s = d["summary"]
            # MAD: Median absolute deviation
            print("{}: value median {:.5f}  MAD: {:.5f}".format(key, s["p50"], s["MAD"]))
        if "diff_summary" in d:
            s = d["diff_summary"]
            print("{}: diff median {:.5f}  MAD: {:.5f}".format(key, s["p50"], s["MAD"]))


    def _getOperatorStats(self, data):
        pass
