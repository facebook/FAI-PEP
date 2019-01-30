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

from regression_detectors.delay_detector.delay_detector \
    import DelayRegressionDetector
from utils.utilities import getDirectory
from utils.custom_logger import getLogger
from utils.utilities import getFilename

detectors = {
    'delay': DelayRegressionDetector,
}


def getRegressionDetectors():
    return detectors


def checkRegressions(info, platform, framework, benchmark,
                     reporters, meta, outdir):
    if meta["metric"] not in detectors:
        return
    commit = info["treatment"]["commit"]
    getLogger().info("Checking regression for " + commit)
    regressions, infos = _detectRegression(info, meta, outdir)
    if len(regressions):
        from driver.benchmark_driver import runOneBenchmark
        getLogger().info(
            "Regression detected on {}, ".format(platform.getMangledName()) +
            "verifying: {}".format(",".join(regressions)))
        for i in infos:
            i["run_type"] = "verify"
            runOneBenchmark(i, benchmark, framework, platform,
                            meta["backend"], reporters)
        verify_regressions, _ = _detectRegression(info, meta, outdir)
        if len(verify_regressions) > 0:
            # regression verified
            regressed_info = infos[-2]
            regressed_info["run_type"] = "regress"
            regressed_info["regressed_types"] = verify_regressions
            runOneBenchmark(regressed_info, benchmark, framework, platform,
                            meta["backend"], reporters)
            getLogger().info("Regression confirmed for commit: {}".
                             format(regressed_info["treatment"]["commit"]))
            getLogger().info("Regressed types: {}".
                             format(",".join(verify_regressions)))
        getLogger().info("Regression verifying completed for " +
                         "{} on {}".format(platform.getMangledName(), commit))
    else:
        getLogger().info("No Regression found for " +
                         "{} on {}".format(platform.getMangledName(), commit))


# Regress is identified if last two runs are both above threshhold.
def _detectOneBenchmarkRegression(data):
    regressed = []
    if 'meta.txt' not in data:
        getLogger().error("Meta is not found")
        return regressed
    meta = data.pop('meta.txt')
    if len(meta) < 2:
        return regressed, None
    control_commits = {x['control_commit'] if 'control_commit' in x
                       else x['commit'] for x in meta}
    control_change = len(control_commits) > 1
    metric = meta[0]["metric"]
    detector = detectors[metric]()
    for filename, one_data in data.items():
        if filename == 'meta.txt':
            continue
        if len(one_data) < 2:
            continue
        if (detector.isRegressed(filename, one_data[0], one_data[2:],
                                 control_change)) and \
            detector.isRegressed(filename, one_data[1], one_data[2:],
                                 control_change):
            regressed.append(one_data[0]["type"])
    if len(regressed) > 0:
        infos = []
        for x in meta:
            idx = x['command'].index("--info")
            infos.append(json.loads(x['command'][idx+1]))
        infos.reverse()
        return regressed, infos
    return regressed, None


def _detectRegression(info, meta, outdir):
    dirs = _getBenchmarkRuns(info, meta, outdir)
    data = _collectBenchmarkRunData(dirs)
    return _detectOneBenchmarkRegression(data)


def _listdirs(path):
    return [x for x in os.listdir(path) if os.path.isdir(path + x)]


def _listfiles(path):
    return [x for x in os.listdir(path) if os.path.isfile(path + x)]


def _getLatestRun(dir):
    runs = _listdirs(dir)
    last_run = 0
    while str(last_run) in runs:
        last_run += 1
    last_run -= 1
    if last_run >= 0:
        return os.path.join(dir, str(last_run))
    else:
        getLogger().error("Latest run in directory %s doesn't exist. "
                          "This should not happen." % dir)
        return None


def _getBenchmarkRuns(info, meta, outdir):
    dir_name = os.path.join(outdir, getFilename(meta["platform"]),
        getFilename(meta["framework"]),
        getFilename(meta["net_name"]),
        getFilename(meta["metric"]),
        getFilename(meta["identifier"]))

    assert "regression_commits" in info, \
        "regression_commits field is missing from info"

    dirs = []
    for entry in info["regression_commits"]:
        one_dir = os.path.jon(dir_name, getDirectory(entry["commit"],
                                          entry["commit_time"]))
        if not os.path.isdir(one_dir):
            continue

        last_run = _getLatestRun(one_dir)
        if last_run is None:
            continue
        dirs.append(last_run)
    return dirs


def _collectBenchmarkRunData(runs):
    data = {}
    if len(runs) == 0:
        # last run failed
        return data
    latest_run = runs.pop(0)
    files = _listfiles(latest_run)
    for filename in files:
        latest_file = latest_run + filename
        if not os.path.isfile(latest_file):
            continue
        with open(latest_file, 'r') as f:
            content = json.load(f)
            d = [content]
            for run in runs:
                compare_file = run + filename
                if not os.path.isfile(compare_file):
                    continue
                with open(compare_file, 'r') as cf:
                    content = json.load(cf)
                    d.append(content)
            data[filename] = d
    runs.insert(0, latest_run)
    return data
