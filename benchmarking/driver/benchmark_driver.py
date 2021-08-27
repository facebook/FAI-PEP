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

import copy
import gc
import os
import string
import sys
import time
import traceback

import numpy as np
from utils.custom_logger import getLogger
from utils.utilities import getCommand, deepMerge, setRunStatus, getRunStatus


def runOneBenchmark(
    info,
    benchmark,
    framework,
    platform,
    backend,
    reporters,
    lock,
    cooldown=None,
    user_identifier=None,
    local_reporter=None,
):
    assert "treatment" in info, "Treatment is missing in info"
    getLogger().info("Running {}".format(benchmark["path"]))

    status = 0
    minfo = copy.deepcopy(info["treatment"])
    mbenchmark = copy.deepcopy(benchmark)
    if "shared_libs" in info:
        minfo["shared_libs"] = info["shared_libs"]
    try:
        # invalidate CPU cache
        [1.0 for _ in range(20 << 20)]
        gc.collect()
        data = _runOnePass(minfo, mbenchmark, framework, platform)
        status = status | getRunStatus()
        meta = None
        if "control" in info:
            cinfo = copy.deepcopy(info["control"])
            if "shared_libs" in info:
                cinfo["shared_libs"] = info["shared_libs"]
            # cool down between treatment and control
            if "model" in benchmark and "cooldown" in benchmark["model"]:
                cooldown = float(benchmark["model"]["cooldown"])
            time.sleep(cooldown)
            # invalidate CPU cache
            [1.0 for _ in range(20 << 20)]
            gc.collect()
            control = _runOnePass(cinfo, benchmark, framework, platform)
            status = status | getRunStatus()
            bname = benchmark["model"]["name"]
            data = _mergeDelayData(data, control, bname)
        if benchmark["tests"][0]["metric"] != "generic":
            data = _adjustData(info, data)
        meta = _retrieveMeta(
            info, benchmark, platform, framework, backend, user_identifier
        )
        data = _retrieveInfo(info, data)
        result = {"meta": meta, "data": data}
    except Exception as e:
        # Catch all exceptions so that failure in one test does not
        # affect other tests
        getLogger().info("Exception caught when running benchmark")
        getLogger().info(e)
        data = None
        status = 2
        setRunStatus(status)
        getLogger().error(traceback.format_exc())

        # Set result meta and data to default values to that
        # the reporter will not try to key into a None
        result = {"meta": {}, "data": []}

    if data is None or len(data) == 0:
        _logNoData(benchmark, info, platform.getMangledName())
        return status

    with lock:
        for reporter in reporters:
            reporter.report(result)

    if (
        "regression_commits" in info
        and info["run_type"] == "benchmark"
        and local_reporter
    ):
        from regression_detectors.regression_detectors import checkRegressions

        checkRegressions(
            info,
            platform,
            framework,
            benchmark,
            reporters,
            result["meta"],
            local_reporter,
        )
    return status


def _logNoData(benchmark, info, name):
    model_name = ""
    if "model" in benchmark and "name" in benchmark["model"]:
        model_name = benchmark["model"]["name"]
    commit_hash = ""
    if "commit" in info["treatment"]:
        commit_hash = info["treatment"]["commit"]
    getLogger().info(
        "No data collected for {}".format(model_name)
        + "on {}. ".format(name)
        + "The run may be failed for "
        + "{}".format(commit_hash)
    )


def _runOnePass(info, benchmark, framework, platform):
    assert (
        len(benchmark["tests"]) == 1
    ), "At this moment, only one test exists in the benchmark"
    to = benchmark["model"]["repeat"] if "repeat" in benchmark["model"] else 1
    output = None
    for idx in range(to):
        benchmark["tests"][0]["INDEX"] = idx
        one_output, output_files = framework.runBenchmark(info, benchmark, platform)
        if output:
            deepMerge(output, one_output)
        else:
            output = copy.deepcopy(one_output)
        if getRunStatus() != 0:
            # early exit if there is an error
            break
    data = _processDelayData(output, benchmark)
    return data


def _processDelayData(input_data, benchmark):
    if not isinstance(input_data, dict):
        return input_data
    data = {}
    for k in input_data:
        d = input_data[k]
        data[k] = copy.deepcopy(d)

        if "values" in d:
            if "summary" not in d:
                data[k]["summary"] = _getStatistics(d["values"], benchmark)
            if "num_runs" not in d:
                data[k]["num_runs"] = len(data[k]["values"])
    return data


def _mergeDelayData(treatment_data, control_data, bname):
    data = copy.deepcopy(treatment_data)
    # meta is not a metric, so handle is seperatly
    data["meta"] = _mergeDelayMeta(treatment_data["meta"], control_data["meta"], bname)
    for k in treatment_data:
        # meta was already merged, so don't try to merge it again
        if k == "meta":
            continue
        if k not in control_data:
            getLogger().error(
                "Value {} existed in treatment but not ".format(k)
                + "control for benchmark {}".format(bname)
            )
            continue
        control_value = control_data[k]
        treatment_value = treatment_data[k]
        if "info_string" in treatment_value:
            assert (
                "info_string" in control_value
            ), "Control value missing info_string field"
            # If the treatment and control are not the same,
            # treatment value is used, the control value is lost.
            treatment_string = treatment_value["info_string"]
            control_string = control_value["info_string"]
            if treatment_string != control_string:
                getLogger().warning(
                    "Treatment value is used, and the control value is lost. "
                    + "The field info_string in control "
                    + "({})".format(control_string)
                    + "is different from the info_string in treatment "
                    + "({})".format(treatment_string)
                )

        if "values" in control_value:
            data[k]["control_values"] = control_value["values"]

        if "summary" in control_value:
            data[k]["control_summary"] = control_value["summary"]
            assert "summary" in treatment_value, "Summary is missing in treatment"
        # create diff of delay
        if "summary" in control_value and "summary" in treatment_value:
            data[k]["diff_summary"] = _createDiffOfDelay(
                control_value["summary"], treatment_value["summary"]
            )

    return data


def _percentileArgVal(token) -> float:
    index = 0
    if token[0] == "-" or token[0] == "+":  # not currently used
        index = 1
    if token[index] != "p":
        return None

    number = token[index + 1 :]
    if not number.isdecimal:
        return None

    percentile = float(number)
    return percentile if percentile >= 0 and percentile <= 100 else None


def _createDiffOfDelay(csummary, tsummary):
    # create diff of delay
    diff_summary = {}
    for value in tsummary:
        arg = _percentileArgVal(value)
        if arg:
            reflection = "p" + string(100 - arg)
            if reflection in csummary:
                diff_summary[value] = tsummary[value] - csummary[reflection]
        elif value in csummary:
            diff_summary[value] = tsummary[value] - csummary[value]

    return diff_summary


def _mergeDelayMeta(treatment_meta, control_meta, bname):
    meta = copy.deepcopy(treatment_meta)
    for k in treatment_meta:
        if k not in control_meta:
            getLogger().error(
                "Value {} existed in treatment but not ".format(k)
                + "control for benchmark {}".format(bname)
            )
            continue
        meta["control_{}".format(k)] = control_meta[k]
    return meta


def _processErrorData(treatment_files, golden_files, benchmark):
    treatment_outputs = _collectErrorData(treatment_files)
    golden_outputs = _collectErrorData(golden_files)
    data = {}
    for output in treatment_outputs:
        treatment_values = treatment_outputs[output]
        assert output in golden_outputs, "Output {} is missing in golden".format(output)
        golden_values = golden_outputs[output]
        diff_values = list(
            map(lambda pair: pair[0] - pair[1], zip(treatment_values, golden_values))
        )
        diff_values.sort()
        treatment_values.sort()
        golden_values.sort()
        data[output] = {
            "summary": _getStatistics(treatment_values, benchmark),
            "control_summary": _getStatistics(golden_values, benchmark),
            "diff_summary": _getStatistics(diff_values, benchmark),
        }
        data[output]["type"] = output
        data[output]["num_runs"] = len(treatment_values)
    return data


def _collectErrorData(output_files):
    data = {}
    for output in output_files:
        filename = output_files[output]
        assert os.path.isfile(filename), "File {} doesn't exist".format(filename)
        with open(filename, "r") as f:
            content = f.read().splitlines()
            data[output] = [float(x.strip()) for x in content]
    return data


def _getStatisticsSet(test):
    if "statistics" in test:
        result = test["statistics"]
        if "p50" not in result:
            result.append(
                "p50"
            )  # always include p50 since it is needed for internal calculations

        getLogger().info("Using custom statistics ({}).".format(result))
        return result
    else:
        # defaults
        # getLogger().info("Using standard statistics.")
        return ["mean", "p0", "p10", "p50", "p90", "p100", "stdev", "MAD", "cv"]


def _getStatistics(array, benchmark):
    test = benchmark["tests"][0]
    statsSet = _getStatisticsSet(test)

    sorted_array = sorted(array)
    median = _getMedian(sorted_array)
    mean = _getMean(array)
    stdev = _getStdev(array, mean)

    metaValues = {
        "mean": mean,
        "stdev": stdev,
        "MAD": _getMedian(sorted(map(lambda x: abs(x - median), sorted_array))),
        "cv": stdev / mean if mean != 0 else None,
    }

    results = {}
    for stat in statsSet:
        if stat in metaValues:
            results[stat] = metaValues[stat]
        else:
            percentileArgVal = _percentileArgVal(stat)  # parses p0-p100
            if percentileArgVal is None:
                getLogger().warning(
                    "Unsupported custom statistic '{}' ignored.".format(stat)
                )
            else:
                results[stat] = np.percentile(sorted_array, percentileArgVal)

    return results


def _getMean(values):
    return sum(values) / len(values)


def _getStdev(values, mean):
    sq_diffs = [(x - mean) ** 2 for x in values]
    return (sum(sq_diffs) / len(values)) ** 0.5


def _getMedian(values):
    length = len(values)
    return (
        values[length // 2]
        if (length % 2) == 1
        else (values[(length - 1) // 2] + values[length // 2]) / 2
    )


def _adjustData(info, data):
    if "regressed_types" not in info:
        return data
    assert (
        "run_type" in info and info["run_type"] == "regress"
    ), "Regressed types only show up in regress run type"
    for v in data:
        if v in info["regressed_types"]:
            data[v]["regressed"] = 1
    return data


def _retrieveMeta(info, benchmark, platform, framework, backend, user_identifier):
    assert "treatment" in info, "Treatment is missing in info"
    meta = {}
    # common
    meta["backend"] = backend
    meta["time"] = time.time()
    meta["framework"] = framework.getName()
    meta["platform"] = platform.getName()
    if platform.platform_hash:
        meta["platform_hash"] = platform.platform_hash
    meta["command"] = sys.argv
    meta["command_str"] = getCommand(sys.argv)
    if user_identifier:
        meta["user_identifier"] = user_identifier

    # model specific
    if "model" in benchmark:
        model = benchmark["model"]
        meta["net_name"] = model["name"]
        if "group" in benchmark["model"]:
            meta["group"] = benchmark["model"]["group"]

    # test specific
    test = benchmark["tests"][0]
    meta["statistics"] = _getStatisticsSet(test)

    meta["metric"] = test["metric"]
    if "identifier" in test:
        meta["identifier"] = test["identifier"]
    else:
        meta["identifier"] = meta["net_name"]

    # info specific
    if "commit" in info["treatment"]:
        meta["commit"] = info["treatment"]["commit"]
        meta["commit_time"] = info["treatment"]["commit_time"]
    if "control" in info:
        meta["control_commit"] = info["control"]["commit"]
        meta["control_commit_time"] = info["control"]["commit_time"]
    if "run_type" in info:
        meta["run_type"] = info["run_type"]

    # Local run, user specific information
    if "user" in info:
        meta["user"] = info["user"]

    return meta


def _retrieveInfo(info, data):
    if "treatment" in info:
        if "meta" not in data:
            data["meta"] = {}
        data["meta"]["treatment_diff"] = info["treatment"].get("diff", "")
        # For early detection, we have treatment version info.
        data["meta"]["treatment_version"] = info["treatment"].get("version", "")
        # For post detection, we have treatment commit info.
        data["meta"]["treatment_commit"] = info["treatment"].get("commit", "")
    if "control" in info and "diff" in info["control"]:
        if "meta" not in data:
            data["meta"] = {}
        # For control, we should always have commit info.
        data["meta"]["control_diff"] = info["control"].get("diff", "")
        data["meta"]["control_commit"] = info["control"].get("commit", "")

    return data
