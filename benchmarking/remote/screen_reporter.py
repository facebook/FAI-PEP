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
import json
import time


class ScreenReporter(object):
    def __init__(self, xdb, devices, debug=False):
        self.xdb = xdb
        self.devices = devices
        self.debug = debug

    def run(self, user_identifier, urlPrefix=None):
        done = False
        statuses = {}
        while not done:
            done = self._runOnce(user_identifier, statuses)
            time.sleep(1)
        if urlPrefix:
            print("You can find more info via {}{}".format(
                urlPrefix, user_identifier))

    def _runOnce(self, user_identifier, statuses):
        new_statuses = self.xdb.statusBenchmarks(user_identifier)
        if len(new_statuses) == 0:
            return False
        for s in new_statuses:
            if s["id"] not in statuses:
                statuses[s["id"]] = s["status"]
                self._display(s)
            else:
                if statuses[s["id"]] != s["status"]:
                    statuses[s["id"]] = s["status"]
                    self._display(s)
        for s in statuses:
            status = statuses[s]
            if status != "DONE" and status != "FAILED" and status != "USER_ERROR":
                return False
        return True

    def _display(self, s):
        abbrs = self.devices.getAbbrs(s["device"])
        print("Job status for {}".format(s["device"]) +
            (" (" + ",".join(abbrs) + ")" if abbrs else "") +
            " is changed to {}".format(s["status"]))
        self._displayResult(s)

    def _printLog(self, r):
        log = r["log"]
        outputs = log.split("\n")
        for o in outputs:
            print(o)

    def _displayResult(self, s):
        if s["status"] != "DONE" and s["status"] != "FAILED" and \
                s["status"] != "USER_ERROR":
            return
        output = self.xdb.getBenchmarks(str(s["id"]))
        for r in output:
            if s["status"] == "DONE":
                res = json.loads(r["result"])
                benchmarks = json.loads(r["benchmarks"])
                metric = benchmarks["benchmark"]["content"]["tests"][0]["metric"]
                for identifier in res:
                    data = res[identifier]
                    if "NET latency" in data:
                        net_latency = data["NET latency"]
                        if "p50" in net_latency["summary"]:
                            net_delay = data["NET latency"]["summary"]["p50"]
                        elif "mean" in net_latency["summary"]:
                            net_delay = data["NET latency"]["summary"]["mean"]
                        else:
                            assert False, "Net latency is not specified"
                        print("ID:{}\tNET latency: {}".format(identifier,
                                                             net_delay))
                        if self.debug:
                            self._printLog(r)
                    elif metric == "generic":
                        # dump std printout to screen for custom_binary
                        if isinstance(data, list):
                            data = '\n'.join(data)
                        print(data)
            else:
                self._printLog(r)
