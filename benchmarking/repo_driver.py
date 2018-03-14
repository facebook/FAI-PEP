#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from collections import deque
import datetime
import json
import os
import shutil
import threading
import time
from utils.arg_parse import getParser, getArgs, \
                                         getUnknowns, parseKnown
from repos.repos import getRepo
from utils.custom_logger import getLogger
from utils.subprocess_with_logger import processRun
from utils.utilities import getDirectory

getParser().add_argument("--base_commit",
    help="In A/B testing, this is the control commit that is used to compare against. " +
    "If not specified, the default is the first commit in the week in UTC timezone. " +
    "Even if specified, the control is the later of the specified commit and the commit at the start of the week.")
getParser().add_argument("--branch", default="master",
    help="The remote repository branch. Defaults to master")
getParser().add_argument("--commit", default="master",
    help="The commit this benchmark runs on. It can be a branch. Defaults to master. " +
    "If it is a commit hash, and program runs on continuous mode, it is the starting " +
    "commit hash the regression runs on. The regression runs on all commits starting from "
    "the specified commit.")
getParser().add_argument("--commit_file",
    help="The file saves the last commit hash that the regression has finished. " +
    "If this argument is specified and is valid, the --commit has no use.")
getParser().add_argument("--exec_dir", required=True,
    help="The executable is saved in the specified directory. " +
    "If an executable is found for a commit, no re-compilation is performed. " +
    "Instead, the previous compiled executable is reused.")
getParser().add_argument("--framework", required=True,
    choices=["caffe2"],
    help="Specify the framework to benchmark on.")
getParser().add_argument("--frameworks_dir", required=True,
    help="Required. The root directory that all frameworks resides. "
    "Usually it is the specifications/frameworks directory.")
getParser().add_argument("--interval", type=int,
    help="The minimum time interval in seconds between two benchmark runs.")
getParser().add_argument("--platforms", required=True,
    help="Specify the platforms to benchmark on, in comma separated list."
    "Use this flag if the framework"
    " needs special compilation scripts. The scripts are called build.sh "
    "saved in specifications/frameworks/<framework>/<platforms> directory")
getParser().add_argument("--regression", action="store_true",
    help="Indicate whether this run detects regression.")
getParser().add_argument("--remote_repository", default="origin",
    help="The remote repository. Defaults to origin")
getParser().add_argument("--repo", default="git",
    choices=["git", "hg"],
    help="Specify the source control repo of the framework.")
getParser().add_argument("--repo_dir", required=True,
    help="Required. The base framework repo directory used for benchmark.")
getParser().add_argument("--same_host", action="store_true",
    help="Specify whether the build and benchmark run are on the same host. "
    "If so, the build cannot be done in parallel with the benchmark run.")
getParser().add_argument("--status_file",
    help="A file to inform the driver stops running when the content of the file is 0.")


def stopRun():
    if getArgs().status_file and os.path.isfile(getArgs().status_file):
        with open(getArgs().status_file, 'r') as file:
            content = file.read().strip()
            if content == "0":
                return True
    return False


class ExecutablesBuilder (threading.Thread):
    def __init__(self, repo, work_queue, queue_lock):
        threading.Thread.__init__(self)
        self.repo = repo
        self.work_queue = work_queue
        self.queue_lock = queue_lock
        self.current_commit_hash = None

    def run(self):
        if getArgs().interval:
            while not stopRun():
                self._buildExecutables()
                time.sleep(getArgs().interval)
        else:
            # single run
            self._buildExecutables()

    def _buildExecutables(self):
        platforms = getArgs().platforms.split(",")
        while not stopRun() and self._pullNewCommits():
            for platform in platforms:
                self._saveOneCommitExecutable(platform)

    def _saveOneCommitExecutable(self, platform):
        getLogger().info("Building executable on {} ".format(platform) +
                         "@ {}".format(self.current_commit_hash))
        same_host = getArgs().same_host
        if same_host:
            self.queue_lock.acquire()
        repo_info = self._buildOneCommitExecutable(platform,
                                                   self.current_commit_hash)
        if repo_info is None:
            getLogger().error(
                "Failed to extract repo commands. Skip this commit.")
        else:
            if not same_host:
                self.queue_lock.acquire()
            self.work_queue.append(repo_info)
        if self.queue_lock.locked():
            self.queue_lock.release()

    def _buildOneCommitExecutable(self, platform, commit_hash):
        repo_info = {}
        repo_info_treatment = self._setupRepoStep(platform, commit_hash)
        if repo_info_treatment is None:
            return None
        repo_info['treatment'] = repo_info_treatment

        if getArgs().regression:
            # only build control on regression detection
            # figure out the base commit. It is the first commit in the week
            control_commit_hash = self._getControlCommit(
                repo_info_treatment['commit_time'], getArgs().base_commit)

            repo_info_control = self._setupRepoStep(platform,
                                                    control_commit_hash)
            if repo_info_control is None:
                return None
            repo_info['control'] = repo_info_control

            repo_info["regression_commits"] = \
                self._getCompareCommits(repo_info_treatment['commit'])
        # use repo_info to pass the value of platform
        repo_info['platform'] = platform
        return repo_info

    def _getCompareCommits(self, latest_commit):
        commits = self.repo.getPriorCommits(latest_commit, 12)
        if not commits:
            return []
        commits = commits.split('\n')
        if commits[-1] == '':
            commits.pop()
        res = []
        for commit in commits:
            c = commit.split(":")
            assert len(c) == 2, "Length is incorrect"
            res.append({"commit": c[0], "commit_time": int(float(c[1]))})
        return res

    def _pullNewCommits(self):
        # first get into the correct branch
        self.repo.checkout(getArgs().branch)
        self.repo.pull(getArgs().remote_repository, getArgs().branch)
        new_commit_hash = None
        if not getArgs().interval:
            new_commit_hash = self._getSavedCommit() \
                if getArgs().commit_file \
                else self.repo.getCommitHash(getArgs().commit)
            if new_commit_hash is None:
                getLogger().error("Commit is not specified")
                return False
        else:
            if self.current_commit_hash is None:
                self.current_commit_hash = self._getSavedCommit()

            if self.current_commit_hash is None:
                new_commit_hash = self.repo.getCommitHash(getArgs().commit)
            else:
                new_commit_hash = self.repo.getNextCommitHash(
                    self.current_commit_hash)
        if new_commit_hash == self.current_commit_hash:
            getLogger().info("Commit %s is already processed, sleeping...",
                             new_commit_hash)
            return False
        self.current_commit_hash = new_commit_hash
        return True

    def _getSavedCommit(self):
        if getArgs().commit_file and \
                os.path.isfile(getArgs().commit_file):
            with open(getArgs().commit_file, 'r') as file:
                commit_hash = file.read().strip()
                # verify that the commit exists
                return self.repo.getNextCommitHash(commit_hash)
        return None

    def _setupRepoStep(self, platform, commit):
        repo_info = {}
        repo_info['commit'] = self.repo.getCommitHash(commit)
        repo_info['commit_time'] = self.repo.getCommitTime(repo_info['commit'])
        return repo_info if self._buildProgram(platform, repo_info) else None

    def _buildProgram(self, platform, repo_info):
        directory = "/" + \
            getDirectory(repo_info['commit'], repo_info['commit_time'])

        dst = getArgs().exec_dir + "/" + getArgs().framework + "/" + \
            platform + "/" + directory + getArgs().framework + \
            "_benchmark"

        repo_info["program"] = dst
        if os.path.isfile(dst):
            return True
        else:
            return self._buildProgramPlatform(repo_info, dst, platform)

    def _buildProgramPlatform(self, repo_info, dst, platform):
        self.repo.checkout(repo_info['commit'])
        script = self._getBuildScript(platform)
        dst_dir = os.path.dirname(dst)
        shutil.rmtree(dst_dir, True)
        os.makedirs(dst_dir)

        if processRun(['sh', script, getArgs().repo_dir, dst]) is not None:
            os.chmod(dst, 0o777)

        if not os.path.isfile(dst):
            getLogger().error(
                "Build program using script {} failed.".format(script))
            return False
        return True

    def _getBuildScript(self, platform):
        assert os.path.isdir(getArgs().frameworks_dir), \
            "Frameworks dir is not specified."
        frameworks_dir = getArgs().frameworks_dir
        assert os.path.isdir(frameworks_dir), \
            "{} must be specified.".format(frameworks_dir)
        framework_dir = frameworks_dir + "/" + getArgs().framework
        assert os.path.isdir(framework_dir), \
            "{} must be specified.".format(framework_dir)
        platform_dir = framework_dir + "/" + platform
        build_script = None
        if os.path.isdir(platform_dir):
            if os.path.isfile(platform_dir + "/build.sh"):
                build_script = platform_dir + "/build.sh"
        if build_script is None:
            # Ideally, should check the parent directory until the
            # framework directory. Save this for the future
            build_script = framework_dir + "/build.sh"
            getLogger().warning("Directory {} ".format(platform_dir) +
                                "doesn't exist. Use " +
                                "{} instead".format(framework_dir))
        assert os.path.isfile(build_script), \
            "Cannot find build script in {} for ".framework_dir + \
            "platform {}".format(platform)
        return build_script

    def _getControlCommit(self, reference_time, base_commit):
        # Get start of week
        dt = datetime.datetime.fromtimestamp(reference_time,
                                             datetime.timezone.utc)
        monday = dt - datetime.timedelta(days=dt.weekday())
        start_of_week = monday.replace(hour=0, minute=0,
                                       second=0, microsecond=0)
        ut_start_of_week = start_of_week.timestamp()

        if base_commit:
            base_commit_time = self.repo.getCommitTime(base_commit)
            if base_commit_time >= ut_start_of_week:
                return base_commit

        # Give more buffer to the date range to avoid the timezone issues
        start = start_of_week - datetime.timedelta(days=1)
        end = dt + datetime.timedelta(days=1)
        logs_str = self.repo.getCommitsInRange(start, end)
        logs = logs_str.split('\n')
        for row in logs:
            items = row.strip().split(':')
            assert len(items) == 2, "Repo log format is wrong"
            commit_hash = items[0].strip()
            unix_time = int(float(items[1].strip()))
            if unix_time >= ut_start_of_week:
                return commit_hash
        assert False, "Cannot find the control commit"
        return None


class RepoDriver(object):
    def __init__(self):
        parseKnown()
        self.repo = getRepo()
        self.queue_lock = threading.Lock()
        self.work_queue = deque()
        self.executables_builder = ExecutablesBuilder(self.repo,
                                                      self.work_queue,
                                                      self.queue_lock)

    def run(self):
        getLogger().info(
            "Start benchmark run @ %s" %
            datetime.datetime.now().isoformat(' '))
        self.executables_builder.start()
        self._runBenchmarkSuites()

    def _runBenchmarkSuites(self):
        # initially sleep 10 seconds in case no need to build the binary
        time.sleep(10)
        if getArgs().interval:
            while not stopRun():
                self._runBenchmarkSuitesInQueue()
                time.sleep(getArgs().interval)
        else:
            # single run
            while self.executables_builder.is_alive():
                time.sleep(10)
            self._runBenchmarkSuitesInQueue()

    def _runBenchmarkSuitesInQueue(self):
        same_host = getArgs().same_host
        while not stopRun() and self.work_queue:
            # we can do this because this is the only
            # consumer of the work_queue
            self.queue_lock.acquire()
            repo_info = self.work_queue.popleft()
            if not same_host:
                self.queue_lock.release()
            self._runOneBenchmarkSuite(repo_info)
            if same_host:
                self.queue_lock.release()

    def _runOneBenchmarkSuite(self, repo_info):
        cmd = self._getCommand(repo_info)
        getLogger().info("Running: %s", cmd)
        # always sleep 10 seconds to make the phone in a more
        # consistent state
        time.sleep(10)
        # cannot use subprocess because it conflicts with requests
        os.system(cmd)
        if getArgs().commit_file:
            with open(getArgs().commit_file, 'w') as file:
                file.write(repo_info['treatment']['commit'])
        getLogger().info("Done one benchmark run for " +
                         repo_info['treatment']['commit'])

    def _getCommand(self, repo_info):
        platform = repo_info["platform"]
        # Remove it from repo_info to avoid polution, should clean up later
        del repo_info["platform"]
        dir_path = os.path.dirname(os.path.realpath(__file__))
        unknowns = getUnknowns()
        command = dir_path + "/harness.py " + \
            " --platform \'" + platform + "\'" + \
            " --framework \'" + getArgs().framework + "\'" + \
            (" --info \'" + json.dumps(repo_info) + "\'") + " " + \
            ' '.join(['"' + u + '"' for u in unknowns])
        return command


if __name__ == "__main__":
    app = RepoDriver()
    app.run()
