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
import os
import time

class ScreenReporter(object):
    def __init__(self, xdb, devices, debug=False, log_output_dir=None):
        self.xdb = xdb
        self.devices = devices
        self.debug = debug
        self.log_output_dir = log_output_dir

    def run(self, user_identifier):
        done = False
        statuses = {}
        while not done:
            done = self._runOnce(user_identifier, statuses)
            time.sleep(1)

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
            if status not in ["DONE", "FAILED", "USER_ERROR", "TIMEOUT"]:
                return False
        return True

    def _display(self, s):
        abbrs = self.devices.getAbbrs(s["device"])
        print("Job status for {}".format(s["device"]) +
            (" (" + ",".join(abbrs) + ")" if abbrs else "") +
            " is changed to {}".format(s["status"]))
        self._displayResult(s)

    def _printLog(self, r):
        if self.log_output_dir is None:
            log = r["log"]
            outputs = log.split("\n")
            for o in outputs:
                print(o)
        else:
            try:
                if not os.path.exists(self.log_output_dir):
                    os.makedirs(self.log_output_dir)
                # Use device name to create an output log file in the directory 'log_output_dir'
                output_file_name = self.log_output_dir + "/" + r["device"] + ".txt"
                with open(output_file_name, "w") as outfile:
                    outfile.write(r["log"])
                    print("Logs written for " + r["device"] + " at " + self.log_output_dir)
            except Exception as e:
                print("Caught exception: " + str(e))
                print("Could not write to file specified at " + self.log_output_dir)

    def _displayResult(self, s):
        if s["status"] != "DONE" and s["status"] != "FAILED" and \
                s["status"] != "USER_ERROR":
            return
        output = self.xdb.getBenchmarks(str(s["id"]))
        for r in output:
            if s["status"] == "DONE":
                res = json.loads(r["result"]) if r["result"] else []
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
                            raise AssertionError("Net latency is not specified")
                        print("ID:{}\tNET latency: {}".format(identifier,
                                                             net_delay))
                    elif metric == "generic":
                        if isinstance(data, dict):
                            if "meta" in data:
                                del data["meta"]
                            if not data:
                                return
                        # dump std printout to screen for custom_binary
                        if isinstance(data, list):
                            data = '\n'.join(data)
                        print(data)
                if self.debug:
                    self._printLog(r)
            else:
                self._printLog(r)
