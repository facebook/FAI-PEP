#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

from utils.subprocess_with_logger import processRun

from .repo_base import RepoBase


class HGRepo(RepoBase):
    def __init__(self, dir):
        super(HGRepo, self).__init__(dir)

    def _run(self, cmd, *args):
        hg = ["hg"]
        if self.dir:
            hg.append("-R")
            hg.append(self.dir)
        hg.append(cmd)
        hg.extend(args)
        return "\n".join(processRun(hg)[0])

    def pull(self, *args):
        return self._run("update", args[0])

    def checkout(self, *args):
        self._run("update", *args)

    def getCurrentCommitHash(self):
        commit = self.getCommitHash(None)
        if commit[-1] == "+":
            commit = commit[:-1]
        return self.getCommitHash(commit)

    def getCommitHash(self, commit):
        if commit:
            output = self._run("log", "--template", "<START>{node}<END>", "-r", commit)
        else:
            output = self._run("log", "-l", "1", "--template", "<START>{node}<END>")
        start = output.index("<START>") + len("<START>")
        end = output.index("<END>")
        return output[start:end]

    def getCommitTime(self, commit):
        t = self._run("log", "--template", "<START>{date}<END>", "-r", commit).strip()
        start = t.index("<START>") + len("<START>")
        end = t.index("<END>")
        return int(float(t[start:end]))

    def getNextCommitHash(self, commit, step):
        self.pull(commit)
        res = self._run("next", str(step))
        if res is None:
            return commit
        res = res.split("\n")
        if len(res) > 0 and res[0].strip() == "reached head commit":
            # Not yet have step commits
            return commit
        return self.getCurrentCommitHash()

    def getCommitsInRange(self, start_date, end_date):
        sdate = start_date.strftime("%Y-%m-%d %H:%M:%S")
        # edate = end_date.strftime("%Y-%m-%d %H:%M:%S")
        output = self._run(
            "log",
            "-r",
            'children(first(reverse(::.) & date("<' + sdate + '")))',
            "--template",
            "{node}:{date}\\n",
        ).strip()
        return output

    def getPriorCommits(self, commit, num):
        # do not support prior commits
        return None
