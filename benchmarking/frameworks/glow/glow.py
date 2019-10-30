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
import json
import re
from six import string_types
from frameworks.framework_base import FrameworkBase
from collections import defaultdict


class GlowFramework(FrameworkBase):
    def __init__(self, tempdir, args):
        super(GlowFramework, self).__init__(args)
        self.tempdir = os.path.join(tempdir, self.getName())
        os.makedirs(self.tempdir, 0o777)

    def getName(self):
        return "glow"

    def runBenchmark(self, info, benchmark, platform):
        output, output_files = \
            super(GlowFramework, self).runBenchmark(info, benchmark,
                                                      platform)
        return output, output_files

    def composeRunCommand(self, commands, platform, programs,
                          model, test, model_files,
                          input_files, output_files, shared_libs,
                          preprocess_files=None, main_command=False):
        cmds = super(GlowFramework, self).composeRunCommand(commands, platform,
                programs, model, test, model_files, input_files, output_files,
                shared_libs, preprocess_files, main_command)
        return cmds

    def runOnPlatform(self, total_num, cmd, platform, platform_args,
            converter):
        output, meta = platform.runBenchmark(cmd, platform_args=platform_args)
        results = {}
        self._maybeAddJsonOutput(output, results)
        self._maybeAddTraceOutput(platform, results)
        self._maybeAddBenchSummary(output, results)
        self._maybeAddNetRunnerStats(output, results)
        results["meta"] = meta
        return results

    def _maybeAddJsonOutput(self, output, results):
        if output is None:
            return False
        rows = output
        if isinstance(output, string_types):
            rows = output.split('\n')
        i = 0
        while i < len(rows):
            try:
                parsed = json.loads(rows[i])
                results[parsed["type"] + " " + parsed["metric"]] = parsed
            except json.JSONDecodeError:
                pass
            i += 1

    def _addOrAppendResult(self, results, key, value, record):
        if key not in results.keys():
            results[key] = record
        results[key]["values"].append(value)

    def _maybeAddBenchSummary(self, output, results):
        existingMaps = {"AddBench": (10, 11),
                        "BatchGemmBench": (12, 13),
                        "GemmBench": (12, 13),
                        "GemmParallelBench": (11, 12),
                        "SLSBench": (10, 11),
                        "TransposeBench": (11, 12)}

        fieldMap = defaultdict(lambda: (10, 11))
        for k in existingMaps:
            fieldMap[k] = existingMaps[k]

        if output is None:
            return False
        rows = output
        if isinstance(output, string_types):
            rows = output.split('\n')
        i = 0
        while i < len(rows):
            try:
                fields = rows[i].split(",")
                if fields[0] == "BenchResult":
                    benchName = fields[1]

                    runtimeRecord = {
                        "type": "NET",
                        "metric": "{}:runtime".format(benchName),
                        "unit": "second",
                        "values": []
                    }
                    throughputRecord = {
                        "type": "SECONDARY",
                        "metric": "{}:throughput".format(benchName),
                        "unit": "Gb/second",
                        "values": []
                    }

                    self._addOrAppendResult(results,
                        "NET {}:runtime".format(benchName),
                        float(fields[fieldMap[benchName][0]]), runtimeRecord
                    )
                    self._addOrAppendResult(results,
                        "SECONDARY {}:throughput".format(benchName),
                        float(fields[fieldMap[benchName][1]]), throughputRecord
                    )

            except IndexError:
                pass
            except ValueError:
                pass
            i += 1

    def _maybeAddNetRunnerStats(self, output, results):
        if output is None:
            return False
        rows = output
        if isinstance(output, string_types):
            rows = output.split('\n')
        i = 0
        while i < len(rows):
            m = re.match(r"^individual inference latency \[(\w+)\]: ([0-9]+) us$",
                    rows[i])
            if m:
                if m.groups()[0] == "glow":
                    mtype = "NET"
                else:
                    mtype = "SECONDARY"
                self._addOrAppendResult(results,
                    mtype + " " + m.groups()[0] + " net_runner inference",
                    int(m.groups()[1]), {
                        "type": mtype,
                        "metric": m.groups()[0] + " net_runner inference",
                        "unit": "microsecond",
                        "values": []
                    }
                )
            i += 1

    def _maybeAddTraceOutput(self, platform, results):
        traceFile = os.path.join(platform.getOutputDir(), "trace")
        if not os.path.exists(traceFile):
            return
        with open(traceFile, 'r') as fp:
            line = fp.readline()
            while line:
                try:
                    parsed = json.loads(line.rstrip(", \n\t"))
                    metric = parsed["name"]
                    if not metric:
                        raise ValueError("empty metric")
                    if metric == "inference_e2e":
                        mtype = "NET"
                    else:
                        mtype = "SECONDARY"
                    key = mtype + " " + metric
                    self._addOrAppendResult(results, key, parsed["dur"], {
                        "type": mtype,
                        "metric": metric,
                        "unit": "microsecond",
                        "values": []
                    })
                except json.JSONDecodeError:
                    pass
                except KeyError:
                    pass
                except ValueError:
                    pass
                line = fp.readline()
