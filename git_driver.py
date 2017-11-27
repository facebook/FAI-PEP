#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import datetime
import json
import os
import shutil
import tempfile
import time
from utils.arg_parse import getParser, getArgs, getUnknowns, parseKnown
from utils.git import Git
from utils.custom_logger import getLogger
from utils.subprocess_with_logger import processRun

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
getParser().add_argument("--models_dir", required=True,
    help="Required. The root directory that all models resides.")
getParser().add_argument("--status_file",
    help="A file to inform the driver stops running when the content of the file is 0.")

platforms = getParser().add_mutually_exclusive_group()
platforms.add_argument("--host", action="store_true",
    help="Run the benchmark on the host.")
platforms.add_argument("--android", action="store_true",
    help="Run the benchmark on all connected android devices.")

class GitDriver(object):
    def __init__(self):
        parseKnown()
        self.git = Git(getArgs().git_dir)
        self.control_commit_hash = None
        self.prev_commit_hash = None
        self.git_info = {}

    def runOnce(self, tempdir):
        getLogger().info(
            "Start test run @ %s" % datetime.datetime.now().isoformat(' '))
        if not self._pullNewCommits():
            return False
        temptempdir = tempdir + "/temp/"
        os.mkdir(temptempdir)
        git_info = self._setupGit(tempdir)
        if git_info != None:
            configs = self._processConfig(git_info)
            for config in configs:
                cmds = config.split(' ')
                cmd = [x.strip() for x in cmds]
                cmd.append("--temp_dir")
                cmd.append(temptempdir)
                getLogger().info("Running: %s", ' '.join(cmd))
                # cannot use subprocess because it conflicts with requests
                os.system(' '.join(cmd))
        else:
            getLogger().error("Failed to extract git commands. Skip this commit.")
        shutil.rmtree(temptempdir, True)
        if getArgs().git_commit_file:
            with open(getArgs().git_commit_file, 'w') as file:
                file.write(self.prev_commit_hash)
        getLogger().info("Done one benchmark run.")
        return True

    def run(self):
        tempdir = tempfile.mkdtemp()
        if not getArgs().interval:
            getLogger().info("Single run...")
            self.runOnce(tempdir)
            return
        getLogger().info("Continuous run...")
        interval = getArgs().interval
        while True:
            if getArgs().status_file and os.path.isfile(getArgs().status_file):
                with open(getArgs().status_file, 'r') as file:
                    content = file.read().strip()
                    if content == "0":
                        shutil.rmtree(tempdir, True)
                        getLogger().info("Exiting...")
                        return
            prev_ts = time.time()
            if not self.runOnce(tempdir):
                current_ts = time.time()
                if current_ts < prev_ts + interval:
                    time.sleep(prev_ts + interval - current_ts)

    def _pullNewCommits(self):
        self.git.pull(getArgs().git_repository, getArgs().git_branch)
        new_commit_hash = None
        if self.prev_commit_hash == None:
            self.prev_commit_hash = self._getSavedCommit()

        if self.prev_commit_hash == None:
            new_commit_hash = self.git.getCommitHash(getArgs().git_commit)
        else:
            new_commit_hash = self.git.getNextCommitHash(self.prev_commit_hash)
        if new_commit_hash == self.prev_commit_hash:
            getLogger().info("Commit %s is already processed, sleeping...", new_commit_hash)
            return False
        self.prev_commit_hash = new_commit_hash
        return True

    def _getSavedCommit(self):
        if getArgs().git_commit_file and \
                os.path.isfile(getArgs().git_commit_file):
            with open(getArgs().git_commit_file, 'r') as file:
                commit_hash = file.read().strip()
                # verify that the commit exists
                commits = self.git.run('rev-list', '--reverse', commit_hash+"^..HEAD").strip().split('\n')
                if commits[0] == commit_hash:
                    return commit_hash
        return None


    def _setupGit(self, tempdir):
        git_info = {}
        treatment_dir = tempdir + '/treatment'
        if os.path.isdir(treatment_dir):
            shutil.rmtree(treatment_dir, True)
        os.mkdir(treatment_dir)
        git_info_treatment = self._setupGitStep(treatment_dir, self.prev_commit_hash, False)
        if git_info_treatment is None:
            return None
        git_info['treatment'] = git_info_treatment
        # figure out the base commit. It is the first commit in the week
        control_commit_hash = self._getControlCommit(git_info_treatment['commit_time'], getArgs().git_base_commit)
        # control may not change that frequent
        control_dir = tempdir + '/control'
        if not os.path.isdir(control_dir):
            os.mkdir(control_dir)

        git_info_control = self._setupGitStep(control_dir, control_commit_hash,
            control_commit_hash == self.control_commit_hash)
        if git_info_control is None:
            return None
        git_info['control'] = git_info_control
        if control_commit_hash == self.control_commit_hash:
            getLogger().info("Program for control commit %s has already built" % control_commit_hash)
        self.control_commit_hash = control_commit_hash

        # restore the original commit
        self.git.checkout(getArgs().git_branch)
        return git_info

    def _setupGitStep(self, tempdir, commit, skip_build):
        git_info = {}
        git_info['commit'] = self.git.getCommitHash(commit)
        git_info['commit_time'] = self.git.getCommitTime(git_info['commit'])
        if not skip_build:
            self.git.checkout(commit)
        return git_info if self._buildProgram(tempdir, git_info, skip_build) else None

    def _buildProgram(self, tempdir, git_info, skip_build):
        if getArgs().android:
            src = getArgs().git_dir + \
                '/build_android/bin/caffe2_benchmark'
            dst = tempdir + '/caffe2_benchmark_android'
            build_dir = getArgs().git_dir + "/build_android"
            script = getArgs().git_dir + "/scripts/build_android.sh -DBUILD_BINARY=ON -DBUILD_SHARE_DIR=ON"
        elif getArgs().host:
            src = getArgs().git_dir + \
                '/build/bin/caffe2_benchmark'
            dst = tempdir + '/caffe2_benchmark_host'
            build_dir = getArgs().git_dir + "/build"
            script = getArgs().git_dir + "/scripts/build_local.sh -DBUILD_BINARY=ON -DBUILD_SHARE_DIR=ON"
        else:
            getLogger().error("At least one platform needs to be specified.")
        return self._buildProgramPlatform(git_info, src, dst, build_dir, script, skip_build)

    def _buildProgramPlatform(self, git_info, src, dst, build_dir, script, skip_build):
        if not skip_build:
            shutil.rmtree(build_dir, True)
            if processRun(script.split(' ')) != None:
                shutil.copyfile(src, dst)
                os.chmod(dst, 0o777)
        if os.path.isfile(dst):
            git_info["program"] = dst
        else:
            if skip_build:
                getLogger().error("The build is skipped, but the file " + \
                    "%s doesn't exist." % dst)
            else:
                getLogger().error("Build Caffe2 failed.")
            return False
        return True

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
                ((" --excluded_platforms \"" + x["excluded_platforms"] + "\"") \
                    if x["excluded_platforms"] else "") +
                (" --android" if getArgs().android else "") +
                (" --host" if getArgs().host else "") +
                (" --info \'" + json.dumps(git_info) + "\'") + " " +
                ' '.join(['"' + u + '"' for u in unknowns])
                for x in content["tests"]]
        return configs

    def _getControlCommit(self, reference_time, base_commit):
        # Get start of week
        dt = datetime.datetime.fromtimestamp(reference_time,
            datetime.timezone.utc)
        monday = dt - datetime.timedelta(days=dt.weekday())
        start_of_week = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        ut_start_of_week = start_of_week.timestamp()

        if base_commit:
            base_commit_time = self.git.getCommitTime(base_commit)
            if base_commit_time >= ut_start_of_week:
                return base_commit

        # Give more buffer to the date range to avoid the timezone issues
        start = start_of_week - datetime.timedelta(days=1)
        end = dt + datetime.timedelta(days=1)
        logs_str = self.git.run('log', '--after', start.isoformat(), '--before',
            end.isoformat(), '--reverse', '--pretty=format:%H:%ct').strip()
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

if __name__ == "__main__":
    app = GitDriver()
    app.run()
