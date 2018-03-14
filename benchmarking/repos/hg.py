#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

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
        return processRun(hg)

    def pull(self, *args):
        return self._run('pull', '--rebase')

    def checkout(self, *args):
        self._run('update', *args)

    def getCommitHash(self, commit):
        output = self._run('log', '--template', '{node}', '-r', commit)
        return output

    def getCommitTime(self, commit):
        t = self._run('log', '--template', '{date}',
                      '-r', commit).strip()
        return int(float(t))

    def getNextCommitHash(self, commit):
        # always get the top-of-trunk commit
        c = self._run('log', '--template', '{node}',
                      'tip')
        return c

    def getCommitsInRange(self, start_date, end_date):
        output = self._run('log',
                           '--date',
                           '"' + start_date.isoformat() + " to " +
                           end_date.isoformat() + '"',
                           '--template', '"{node}:{date}\n"').strip()
        return output.reverse()

    def getPriorCommits(self, commit, num):
        assert False, "Not implemented"
