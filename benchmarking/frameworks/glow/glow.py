#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


import json
import os
import re
from collections import defaultdict

from frameworks.framework_base import FrameworkBase
from six import string_types


class GlowFramework(FrameworkBase):
    def __init__(self, tempdir, args):
        super().__init__(args)
        self.tempdir = os.path.join(tempdir, self.getName())
        os.makedirs(self.tempdir, 0o777)

    def getName(self):
        return "glow"

    def runBenchmark(self, info, benchmark, platform):
        output, output_files = super().runBenchmark(info, benchmark, platform)
        return output, output_files

    def composeRunCommand(
        self,
        commands,
        platform,
        programs,
        model,
        test,
        model_files,
        input_files,
        output_files,
        shared_libs,
        preprocess_files=None,
        main_command=False,
    ):
        cmds = super().composeRunCommand(
            commands,
            platform,
            programs,
            model,
            test,
            model_files,
            input_files,
            output_files,
            shared_libs,
            preprocess_files,
            main_command,
        )
        return cmds

    def runOnPlatform(self, total_num, cmd, platform, platform_args, converter):
        output, meta = platform.runBenchmark(cmd, platform_args=platform_args)
        results = {}
        self._maybeAddJsonOutput(output, results)
        self._maybeAddTraceOutput(platform, results)
        self._maybeAddBenchSummary(output, results)
        self._maybeAddNetRunnerStats(output, results)
        self._maybeNetRunner(output, results)
        self._maybeRepro(output, results)
        results["meta"] = meta
        return results

    def _maybeRepro(self, output, results):
        if output is None:
            return False
        rows = output
        if isinstance(output, str):
            rows = output.split("\n")
        i = 0
        while i < len(rows):
            if "Total inference duration (ms): " in rows[i]:
                total_inferece_time = float(
                    rows[i].split("Total inference duration (ms): ")[1]
                )
                self._addOrAppendResult(
                    results,
                    "Total inference duration",
                    total_inferece_time,
                    {
                        "type": "NET",
                        "metric": "Total inference duration",
                        "unit": "ms",
                        "values": [],
                    },
                )
            if "Avg inference duration (ms): " in rows[i]:
                avg_inference_time = float(
                    rows[i].split("Avg inference duration (ms): ")[1]
                )
                self._addOrAppendResult(
                    results,
                    "Avg inference duration",
                    avg_inference_time,
                    {
                        "type": "NET",
                        "metric": "Avg inference duration",
                        "unit": "scalar",
                        "values": [],
                    },
                )
            if "Avg inference per second: " in rows[i]:
                avg_inference_per_second = float(
                    rows[i].split("Avg inference per second: ")[1]
                )
                self._addOrAppendResult(
                    results,
                    "Avg inference per second",
                    avg_inference_per_second,
                    {
                        "type": "NET",
                        "metric": "Avg inference per second",
                        "unit": "scalar",
                        "values": [],
                    },
                )
            i += 1

    def _maybeNetRunner(self, output, results):
        if output is None:
            return False
        rows = output
        if isinstance(output, str):
            rows = output.split("\n")
        i = 0
        while i < len(rows):
            match = re.search(r"(.*)latency per (.*) \[(.*)\]:", rows[i])
            if match:
                if match.group(3) == "glow":
                    mtype = "NET"
                else:
                    mtype = "SECONDARY"
                name = match.group(3)
                latency_kind = match.group(2)
                card = match.group(1)
                if card:
                    latency_kind = "card " + latency_kind
                i += 1
                while i < len(rows) and "latency per" not in rows[i].lower():
                    match = re.search(
                        r".*latency\((.*)\): p(.*): (.*)", rows[i].lower()
                    )
                    if match:
                        unit = match.group(1)
                        percentile = "p" + match.group(2)
                        value = float(match.group(3))

                        self._addOrAppendResult(
                            results,
                            " ".join(
                                [mtype, name, "net_runner", latency_kind, percentile]
                            ),
                            value,
                            {
                                "type": mtype,
                                "metric": " ".join(
                                    [name, "net_runner", latency_kind, percentile]
                                ),
                                "unit": unit,
                                "values": [],
                            },
                        )
                    i += 1
            else:
                i += 1

        i = 0
        while i < len(rows):
            match = re.search(r"(.*): (.*) vs (.*)\((.*)\)", rows[i])
            if match:
                test_impls1, test_impls2 = sorted([match.group(2), match.group(3)])
                i += 1
                while i < len(rows) and "abs error" in rows[i].lower():
                    match = re.search(r".*abs error p(.*): (.*)", rows[i].lower())
                    if match:
                        percentile = "p" + match.group(1)
                        value = float(match.group(2))

                        self._addOrAppendResult(
                            results,
                            " ".join(
                                [
                                    "NET",
                                    test_impls1,
                                    "vs",
                                    test_impls2,
                                    "abs error",
                                    percentile,
                                ]
                            ),
                            value,
                            {
                                "type": "NET",
                                "metric": " ".join(
                                    [
                                        test_impls1,
                                        "vs",
                                        test_impls2,
                                        "abs error",
                                        percentile,
                                    ]
                                ),
                                "unit": "scalar",
                                "values": [],
                            },
                        )
                    i += 1

            else:
                i += 1

    def _maybeAddJsonOutput(self, output, results):
        if output is None:
            return False
        rows = output
        if isinstance(output, str):
            rows = output.split("\n")
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
        existingMaps = {
            "AddBench": (10, 11),
            "BatchGemmBench": (12, 13),
            "GemmBench": (12, 13),
            "GemmParallelBench": (11, 12),
            "SLSBench": (10, 11),
            "TransposeBench": (11, 12),
        }

        fieldMap = defaultdict(lambda: (10, 11))
        for k in existingMaps:
            fieldMap[k] = existingMaps[k]

        if output is None:
            return False
        rows = output
        if isinstance(output, str):
            rows = output.split("\n")
        i = 0
        while i < len(rows):
            try:
                fields = rows[i].split(",")
                if fields[0] == "BenchResult":
                    benchName = fields[1]

                    runtimeRecord = {
                        "type": "NET",
                        "metric": f"{benchName}:runtime",
                        "unit": "second",
                        "values": [],
                    }
                    throughputRecord = {
                        "type": "SECONDARY",
                        "metric": f"{benchName}:throughput",
                        "unit": "Gb/second",
                        "values": [],
                    }

                    self._addOrAppendResult(
                        results,
                        f"NET {benchName}:runtime",
                        float(fields[fieldMap[benchName][0]]),
                        runtimeRecord,
                    )
                    self._addOrAppendResult(
                        results,
                        f"SECONDARY {benchName}:throughput",
                        float(fields[fieldMap[benchName][1]]),
                        throughputRecord,
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
        if isinstance(output, str):
            rows = output.split("\n")
        i = 0
        while i < len(rows):
            m = re.match(
                r"^individual inference latency \[(\w+)\]: ([0-9]+) us$", rows[i]
            )
            if m:
                if m.groups()[0] == "glow":
                    mtype = "NET"
                else:
                    mtype = "SECONDARY"
                self._addOrAppendResult(
                    results,
                    mtype + " " + m.groups()[0] + " net_runner inference",
                    int(m.groups()[1]),
                    {
                        "type": mtype,
                        "metric": m.groups()[0] + " net_runner inference",
                        "unit": "microsecond",
                        "values": [],
                    },
                )
            i += 1

    def _maybeAddTraceOutput(self, platform, results):
        traceFile = os.path.join(platform.getOutputDir(), "trace")
        if not os.path.exists(traceFile):
            return
        with open(traceFile) as fp:
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
                    self._addOrAppendResult(
                        results,
                        key,
                        parsed["dur"],
                        {
                            "type": mtype,
                            "metric": metric,
                            "unit": "microsecond",
                            "values": [],
                        },
                    )
                except json.JSONDecodeError:
                    pass
                except KeyError:
                    pass
                except ValueError:
                    pass
                line = fp.readline()
