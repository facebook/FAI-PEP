#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


from utils.subprocess_with_logger import processRun

from .repo_base import RepoBase


class GitRepo(RepoBase):
    def __init__(self, dir):
        super().__init__(dir)

    def _run(self, cmd, *args):
        git = ["git"]
        if self.dir:
            git.append("-C")
            git.append(self.dir)
        git.append(cmd)
        git.extend(args)
        return "\n".join(processRun(git)[0])

    def pull(self, *args):
        return self._run("pull", *args)

    def checkout(self, *args):
        self._run("checkout", *args)
        self._run("submodule", "sync")
        self._run("submodule", "update", "--init", "--recursive")

    def getCurrentCommitHash(self):
        return self.getCommitHash("HEAD")

    def getCommitHash(self, commit):
        return self._run("rev-parse", commit).rstrip()

    def getCommitTime(self, commit):
        return int(self._run("show", "-s", "--format=%at", commit).strip())

    def getNextCommitHash(self, commit, step):
        commits = (
            self._run("rev-list", "--reverse", "--ancestry-path", commit + "..HEAD")
            .strip()
            .split("\n")
        )
        if len(commits) <= step:
            return commit
        next_commit = commits[step - 1].strip()
        return next_commit

    def getCommitsInRange(self, start_date, end_date):
        return self._run(
            "log",
            "--after",
            start_date.isoformat(),
            "--before",
            end_date.isoformat(),
            "--reverse",
            "--pretty=format:%H:%ct",
        ).strip()

    def getPriorCommits(self, commit, num):
        return self._run(
            "log", "-" + str(num), "--pretty=format:%H:%ct", commit
        ).strip()
