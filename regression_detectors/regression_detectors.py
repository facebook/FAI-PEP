#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import json
import os
import shutil
import tempfile
import threading
import time

from regression_detectors.delay_detector.delay_detector \
    import DelayRegressionDetector
from utils.utilities import getDirectory, getCommand
from utils.custom_logger import getLogger

detectors = {
    'delay': DelayRegressionDetector,
}


def addRegressionDetectors(key, detector):
    global detectors
    detectors[key] = detector


def getRegressionDetectors():
    return detectors


class VerifyRegressions (threading.Thread):
    def __init__(self, regression_data):
        threading.Thread.__init__(self)
        self.regression_data = regression_data

    def run(self):
        tempdir = tempfile.mkdtemp()
        for one_regression in self.regression_data:
            self._runOneRegression(one_regression)
        shutil.rmtree(tempdir, True)

    def _runOneRegression(self, one_regression):
        prefix = one_regression["prefix"]
        meta = one_regression["meta"]
        commands = [x["command"] for x in meta]
        commands.reverse()
        platform = self._getPlatform(meta[0])

        for command in commands:
            self._removeCommandArgs(command)
            command = getCommand(command)
            cmd = command + " --platform '" + platform + "'" + \
                " --run_type verify"
            time.sleep(10)
            getLogger().info("Running: %s", cmd)
            os.system(cmd)
        # get the verify data
        runs = []
        for one_meta in meta:
            date_directory = getDirectory(one_meta["commit"],
                                          one_meta["commit_time"])
            path = prefix + date_directory
            if not os.path.isdir(path):
                getLogger().error("The directory doesn't exist, "
                                  "should not happen")
                continue
            latest_run = _getLatestRun(path)
            if latest_run is None:
                continue
            runs.append(latest_run)
        data = _collectBenchmarkRunData(runs)
        regressed, command = _detectOneBenchmarkRegression(data)
        if len(regressed) > 0:
            getLogger().info("Regression confirmed.")
            # rerun the regressed point and send the final
            # confirmed regressed data
            regressed_types_string = json.dumps(regressed, sort_keys=True)
            self._removeCommandArgs(command)
            command = getCommand(command)
            platform = self._getPlatform(meta[0])
            cmd = command + " --platform '" + platform + "\'" + \
                " --run_type regress --regressed_types '" + \
                regressed_types_string + "'"
            time.sleep(10)
            getLogger().info("Running: %s", cmd)
            os.system(cmd)

    def _removeCommandArgs(self, command):
        self._removeCommandArg(command, "--platform")
        self._removeCommandArg(command, "--run_type")
        self._removeCommandArg(command, "--regressed_types")

    def _removeCommandArg(self, command, arg):
        try:
            idx = command.index(arg)
            assert len(command) > idx+1
            del command[idx]
            del command[idx]
        except ValueError:
            pass

    def _getPlatform(self, meta):
        return meta["platform_hash"] if "platform_hash" in meta \
            else meta["platform"]


def checkRegressions(git, git_info, outdir):
    getLogger().info("Checking regression for " +
                     git_info["treatment"]["commit"])
    regressions = _detectRegression(git, git_info, outdir)
    if len(regressions):
        getLogger().info("Regression detected, verifying")
        drivers = []
        for platform in regressions:
            regression = regressions[platform]
            driver = VerifyRegressions(regression)
            driver.start()
            drivers.append(driver)
        for driver in drivers:
            driver.join()
        getLogger().info("Regression verifying completed")
    else:
        getLogger().info("No Regression found")


# Regress is identified if last two runs are both above threshhold.
def _detectOneBenchmarkRegression(data):
    regressed = []
    if 'meta.txt' not in data:
        getLogger().error("Meta is not found")
        return regressed, None
    meta = data['meta.txt']
    if len(meta) < 2:
        return regressed, None
    control_change = len(set([x['control_commit']
        if 'control_commit' in x else x['commit'] for x in meta])) > 1
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

    command = meta[1]["command"]
    return regressed, command


def _detectRegression(git, git_info, outdir):
    regressions = {}
    dirs = _getBenchmarkRuns(git,
                             git_info['treatment']['commit'],
                             git_info['treatment']['commit_time'],
                             outdir)
    for metric, metric_dir in dirs.items():
        if metric not in detectors:
            getLogger().info("Metric {0} is not defined. ".format(metric) +
                             "Cannot detect regression for it.")
            continue
        for platform, platform_dir in metric_dir.items():
            for net, net_dir in platform_dir.items():
                for metric2, metric_dir2 in net_dir.items():
                    for identifier, identifier_dir in metric_dir2.items():
                        data = _collectBenchmarkRunData(identifier_dir)
                        regressed, _ = _detectOneBenchmarkRegression(data)
                        if len(regressed) > 0:
                            prefix = outdir + "/" + platform + "/" + net + \
                                "/" + metric2 + "/" + identifier + "/"
                            if platform not in regressions:
                                regressions[platform] = []
                            regressions[platform].append({
                                "prefix": prefix,
                                "meta": data['meta.txt']
                            })
                            getLogger().info("Regression detected for [" +
                                             ','.join(regressed) +
                                             "] in " + identifier_dir[0])
    return regressions


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
        return dir + str(last_run) + "/"
    else:
        getLogger().error("Latest run in directory %s doesn't exist. "
                          "This should not happen." % dir)
        return None


def _getLatestBenchmarkRuns(commit, commit_time, outdir):
    dirs = {}
    date_directory = getDirectory(commit, commit_time)
    platforms = _listdirs(outdir)
    for platform in platforms:
        platform_subdir = outdir + platform + "/"
        nets = _listdirs(platform_subdir)
        for net_name in nets:
            net_subdir = platform_subdir + net_name + "/"
            metrics = _listdirs(net_subdir)
            for metric_name in metrics:
                metric_subdir = net_subdir + metric_name + "/"
                ids = _listdirs(metric_subdir)
                for identifier in ids:
                    id_subdir = metric_subdir + identifier + "/" + \
                        date_directory
                    if not os.path.isdir(id_subdir):
                        getLogger().error("The benchmark run for %s does"
                                          "not exist, skiping..." % id_subdir)
                        continue
                    # get the latest run
                    last_run = _getLatestRun(id_subdir)

                    if last_run is None:
                        continue

                    meta = last_run + "meta.txt"
                    if os.path.isfile(meta):
                        with open(meta, 'r') as file:
                            content = json.load(file)
                            metric = content["metric"]
                            if metric not in dirs:
                                dirs[metric] = {}
                            metric_dir = dirs[metric]
                            if platform not in metric_dir:
                                metric_dir[platform] = {}
                            platform_dir = metric_dir[platform]
                            if net_name not in platform_dir:
                                platform_dir[net_name] = {}
                            net_dir = platform_dir[net_name]
                            if metric_name not in net_dir:
                                net_dir[metric_name] = {}
                            metric_dir = net_dir[metric_name]
                            if identifier not in metric_dir:
                                metric_dir[identifier] = []
                            identifier_dir = metric_dir[identifier]
                            identifier_dir.append(last_run)
    return dirs


def _getBenchmarkRuns(git, latest_commit, latest_commit_time, outdir):
    # compose previous 30 commits. If there is no data in the previous
    # 30 commits, the earlier commits may not be meaningful.
    commits = git.run('rev-list', "--max-count=12", latest_commit)
    if not commits:
        return {}
    commits = commits.split('\n')
    # remove the latest commit
    commits.pop(0)
    if commits[-1] == '':
        commits.pop()

    dirs = _getLatestBenchmarkRuns(latest_commit, latest_commit_time, outdir)

    for _, metric_dir in dirs.items():
        for platform, platform_dir in metric_dir.items():
            for net_name, net_dir in platform_dir.items():
                for metric_name, metric_dir2 in net_dir.items():
                    for identifier, identifier_dir in metric_dir2.items():
                        for commit in commits:
                            # get the directory.
                            commit_time = git.getCommitTime(commit)
                            date_directory = getDirectory(commit, commit_time)
                            directory = outdir + platform + \
                                "/" + net_name + "/" + metric_name + "/" + \
                                identifier + "/" + date_directory
                            if not os.path.isdir(directory):
                                continue
                            last_run = _getLatestRun(directory)
                            if last_run is None:
                                continue
                            identifier_dir.append(last_run)
    return dirs


def _collectBenchmarkRunData(runs):
    data = {}
    latest_run = runs.pop(0)
    files = _listfiles(latest_run)
    for filename in files:
        latest_file = latest_run + filename
        if not os.path.isfile(latest_file):
            continue
        with open(latest_file, 'r') as f:
            content = json.load(f)
            data[filename] = [content]
            for run in runs:
                compare_file = run + filename
                if not os.path.isfile(compare_file):
                    continue
                with open(compare_file, 'r') as cf:
                    content = json.load(cf)
                    data[filename].append(content)
    runs.insert(0, latest_run)
    return data
