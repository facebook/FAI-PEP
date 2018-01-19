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
import tempfile
import threading
import time
from regression_detectors.regression_detectors import checkRegressions
from utils.arg_parse import getParser, getArgs, getUnknowns, parseKnown
from utils.git import Git
from utils.custom_logger import getLogger
from utils.subprocess_with_logger import processRun
from utils.utilities import getDirectory

getParser().add_argument("--exec_dir", required=True,
    help="The executable is saved in the specified directory. " +
    "If an executable is found for a commit, no re-compilation is performed. " +
    "Instead, the previous compiled executable is reused.")
getParser().add_argument("--config", required=True,
    help="Required. The test config file containing all the tests to run")
getParser().add_argument("--git_base_commit",
    help="In A/B testing, this is the control commit that is used to compare against. " +
    "If not specified, the default is the first commit in the week in UTC timezone. " +
    "Even if specified, the control is the later of the specified commit and the commit at the start of the week.")
getParser().add_argument("--git_branch", default="master",
    help="The remote git repository branch. Defaults to master")
getParser().add_argument("--git_commit", default="master",
    help="The git commit this benchmark runs on. It can be a branch. Defaults to master. " +
    "If it is a commit hash, and program runs on continuous mode, it is the starting " +
    "commit hash the regression runs on. The regression runs on all commits starting from "
    "the specified commit.")
getParser().add_argument("--git_commit_file",
    help="The file saves the last commit hash that the regression has finished. " +
    "If this argument is specified and is valid, the --git_commit has no use.")
getParser().add_argument("--git_dir", required=True,
    help="Required. The base git directory for Caffe2.")
getParser().add_argument("--git_repository", default="origin",
    help="The remote git repository. Defaults to origin")
getParser().add_argument("--interval", type=int,
    help="The minimum time interval in seconds between two benchmark runs.")
getParser().add_argument("--local_reporter",
    help="Save the result to a directory specified by this argument.")
getParser().add_argument("--models_dir", required=True,
    help="Required. The root directory that all models resides.")
getParser().add_argument("--status_file",
    help="A file to inform the driver stops running when the content of the file is 0.")

platforms = getParser().add_mutually_exclusive_group()
platforms.add_argument("--host", action="store_true",
    help="Run the benchmark on the host.")
platforms.add_argument("--android", action="store_true",
    help="Run the benchmark on all connected android devices.")


def stopRun():
    if getArgs().status_file and os.path.isfile(getArgs().status_file):
        with open(getArgs().status_file, 'r') as file:
            content = file.read().strip()
            if content == "0":
                return True
    return False


class ExecutablesBuilder (threading.Thread):
    def __init__(self, git, work_queue, queue_lock):
        threading.Thread.__init__(self)
        self.git = git
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
        while not stopRun() and self._pullNewCommits():
            git_info = self._buildOneCommitExecutable(self.current_commit_hash)
            if git_info is None:
                getLogger().error(
                    "Failed to extract git commands. Skip this commit.")
            else:
                self.queue_lock.acquire()
                self.work_queue.append(git_info)
                self.queue_lock.release()

    def _buildOneCommitExecutable(self, commit_hash):
        git_info = {}
        git_info_treatment = self._setupGitStep(commit_hash)
        if git_info_treatment is None:
            return None
        git_info['treatment'] = git_info_treatment
        # figure out the base commit. It is the first commit in the week
        control_commit_hash = self._getControlCommit(
            git_info_treatment['commit_time'], getArgs().git_base_commit)

        git_info_control = self._setupGitStep(control_commit_hash)
        if git_info_control is None:
            return None
        git_info['control'] = git_info_control
        return git_info

    def _pullNewCommits(self):
        # first get into the correct branch
        self.git.checkout(getArgs().git_branch)
        self.git.pull(getArgs().git_repository, getArgs().git_branch)
        new_commit_hash = None
        if not getArgs().interval:
            new_commit_hash = self._getSavedCommit() \
                if getArgs().git_commit_file \
                else self.git.getCommitHash(getArgs().git_commit)
            if new_commit_hash is None:
                getLogger().error("Commit is not specified")
                return False

        else:
            if self.current_commit_hash is None:
                self.current_commit_hash = self._getSavedCommit()

            if self.current_commit_hash is None:
                new_commit_hash = self.git.getCommitHash(getArgs().git_commit)
            else:
                new_commit_hash = self.git.getNextCommitHash(
                    self.current_commit_hash)
        if new_commit_hash == self.current_commit_hash:
            getLogger().info("Commit %s is already processed, sleeping...",
                             new_commit_hash)
            return False
        self.current_commit_hash = new_commit_hash
        return True

    def _getSavedCommit(self):
        if getArgs().git_commit_file and \
                os.path.isfile(getArgs().git_commit_file):
            with open(getArgs().git_commit_file, 'r') as file:
                commit_hash = file.read().strip()
                # verify that the commit exists
                commits = self.git.run('rev-list',
                                       '--reverse',
                                       commit_hash+"^..HEAD").\
                    strip().split('\n')
                if commits[0] == commit_hash:
                    return commit_hash
        return None

    def _setupGitStep(self, commit):
        git_info = {}
        git_info['commit'] = self.git.getCommitHash(commit)
        git_info['commit_time'] = self.git.getCommitTime(git_info['commit'])
        return git_info if self._buildProgram(git_info) else None

    def _buildProgram(self, git_info):
        directory = getArgs().exec_dir + "/" + \
            getDirectory(git_info['commit'], git_info['commit_time'])

        if getArgs().android:
            src = getArgs().git_dir + \
                '/build_android/bin/caffe2_benchmark'
            dst = directory + '/android/caffe2_benchmark'
            build_dir = getArgs().git_dir + "/build_android"
            script = getArgs().git_dir + \
                "/scripts/build_android.sh -DBUILD_BINARY=ON " + \
                "-DBUILD_SHARE_DIR=ON -DBUILD_OBSERVERS=ON -DUSE_ZSTD=ON"
        elif getArgs().host:
            src = getArgs().git_dir + \
                '/build/bin/caffe2_benchmark'
            dst = directory + '/host/caffe2_benchmark'
            build_dir = getArgs().git_dir + "/build"
            script = getArgs().git_dir + \
                "/scripts/build_local.sh -DBUILD_BINARY=ON " + \
                "-DBUILD_SHARE_DIR=ON -DBUILD_OBSERVERS=ON -DUSE_ZSTD=ON"
        else:
            getLogger().error("At least one platform needs to be specified.")
        git_info["program"] = dst
        if os.path.isfile(dst):
            return True
        else:
            return self._buildProgramPlatform(
                git_info, src, dst, build_dir, script)

    def _buildProgramPlatform(self, git_info, src, dst, build_dir, script):
        self.git.checkout(git_info['commit'])
        shutil.rmtree(build_dir, True)
        if processRun(script.split(' ')) is not None:
            directory = os.path.dirname(dst)
            if not os.path.isdir(directory):
                os.makedirs(directory)
            shutil.copyfile(src, dst)
            os.chmod(dst, 0o777)

        if not os.path.isfile(dst):
            getLogger().error("Build Caffe2 failed.")
            return False
        return True

    def _getControlCommit(self, reference_time, base_commit):
        # Get start of week
        dt = datetime.datetime.fromtimestamp(reference_time,
                                             datetime.timezone.utc)
        monday = dt - datetime.timedelta(days=dt.weekday())
        start_of_week = monday.replace(hour=0, minute=0,
                                       second=0, microsecond=0)
        ut_start_of_week = start_of_week.timestamp()

        if base_commit:
            base_commit_time = self.git.getCommitTime(base_commit)
            if base_commit_time >= ut_start_of_week:
                return base_commit

        # Give more buffer to the date range to avoid the timezone issues
        start = start_of_week - datetime.timedelta(days=1)
        end = dt + datetime.timedelta(days=1)
        logs_str = self.git.run('log',
                                '--after',
                                start.isoformat(),
                                '--before',
                                end.isoformat(),
                                '--reverse',
                                '--pretty=format:%H:%ct').strip()
        logs = logs_str.split('\n')
        for row in logs:
            items = row.strip().split(':')
            assert len(items) == 2, "Git log format is wrong"
            commit_hash = items[0].strip()
            unix_time = int(items[1].strip())
            if unix_time >= ut_start_of_week:
                return commit_hash
        assert False, "Cannot find the control commit"
        return None


class GitDriver(object):
    def __init__(self):
        parseKnown()
        self.git = Git(getArgs().git_dir)
        self.queue_lock = threading.Lock()
        self.work_queue = deque()
        self.executables_builder = ExecutablesBuilder(self.git,
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
        tempdir = tempfile.mkdtemp()
        while not stopRun() and self.work_queue:
            # we can do this because this is the only
            # consumer of the work_queue
            self.queue_lock.acquire()
            git_info = self.work_queue.popleft()
            self.queue_lock.release()
            self._runOneBenchmarkSuite(git_info, tempdir)
        shutil.rmtree(tempdir, True)

    def _runOneBenchmarkSuite(self, git_info, tempdir):
        configs = self._processConfig(git_info)
        for config in configs:
            cmds = config.split(' ')
            cmd = [x.strip() for x in cmds]
            cmd.append("--temp_dir")
            cmd.append(tempdir)
            getLogger().info("Running: %s", ' '.join(cmd))
            # always sleep 10 seconds to make the phone in a more
            # consistent state
            time.sleep(10)
            # cannot use subprocess because it conflicts with requests
            os.system(' '.join(cmd))
        if getArgs().local_reporter:
            checkRegressions(self.git,
                             git_info,
                             getArgs().local_reporter + "/")
        if getArgs().git_commit_file:
            with open(getArgs().git_commit_file, 'w') as file:
                file.write(git_info['treatment']['commit'])
        getLogger().info("Done one benchmark run for " +
                         git_info['treatment']['commit'])

    def _processConfig(self, git_info):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        models_dir = getArgs().models_dir
        unknowns = getUnknowns()
        with open(getArgs().config, 'r') as file:
            content = json.load(file)
            assert content["tests"], "Test is not specified in the config file"
            configs = [dir_path +
                       "/harness.py " +
                       x["args"].strip().replace('<models_dir>', models_dir) +
                       ((" --platforms \"" + x["platforms"] + "\"")
                        if "platforms" in x and
                        (len(x["platforms"]) > 0) else "") +
                       ((" --excluded_platforms \"" +
                        x["excluded_platforms"] + "\"")
                        if "excluded_platforms" in x and
                        (len(x["excluded_platforms"]) > 0) else "") +
                       ((" --local_reporter " + getArgs().local_reporter)
                        if getArgs().local_reporter else "") +
                       (" --android" if getArgs().android else "") +
                       (" --host" if getArgs().host else "") +
                       (" --info \'" + json.dumps(git_info) + "\'") + " " +
                       ' '.join(['"' + u + '"' for u in unknowns])
                       for x in content["tests"]]
        return configs


if __name__ == "__main__":
    app = GitDriver()
    app.run()
