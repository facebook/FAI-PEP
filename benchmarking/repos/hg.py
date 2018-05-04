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
        return self._run('pull', '--rebase', '-d', args[0])

    def checkout(self, *args):
        self._run('update', *args)

    def getCurrentCommitHash(self):
        commit = self.getCommitHash(None)
        if commit[-1] == '+':
            commit = commit[:-1]
        return self.getCommitHash(commit)

    def getCommitHash(self, commit):
        if commit:
            output = self._run('log', '--template', '<START>{node}<END>',
                               '-r', commit)
        else:
            output = self._run('log', '-l', "1",
                               '--template', '<START>{node}<END>')
        start = output.index('<START>') + len('<START>')
        end = output.index('<END>')
        return output[start:end]

    def getCommitTime(self, commit):
        t = self._run('log', '--template', '<START>{date}<END>',
                      '-r', commit).strip()
        start = t.index('<START>') + len('<START>')
        end = t.index('<END>')
        return int(float(t[start:end]))

    def getNextCommitHash(self, commit, step):
        commit_str = self._run('log', '-T', '<START>{date|hgdate}<END>', '-r', commit)
        start = commit_str.index('<START>') + len('<START>')
        end = commit_str.index('<END>')
        commit_date = commit_str[start:end].split()
        next_commit_date = int(commit_date[0]) + step

        commit_str = self._run('log', '-d', '<' + f'{next_commit_date} {commit_date[1]}', '-l', '1', '--template', '<START>{node}<END>')
        start = commit_str.index('<START>') + len('<START>')
        end = commit_str.index('<END>')
        return commit_str[start:end]

    def getCommitsInRange(self, start_date, end_date):
        sdate = start_date.strftime("%Y-%m-%d %H:%M:%S")
        # edate = end_date.strftime("%Y-%m-%d %H:%M:%S")
        output = self._run('log',
                           '-r',
                           'children(first(reverse(::.) & date(\"<' +
                           sdate + '\")))',
                           '--template', '{node}:{date}\\n'
                           ).strip()
        return output

    def getPriorCommits(self, commit, num):
        # do not support prior commits
        return None
