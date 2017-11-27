#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from utils.subprocess_with_logger import processRun

class Git(object):
    def __init__(self, dir):
        self.dir = dir
        pass

    def run(self, cmd, *args):
        git = ["git"]
        if self.dir:
            git.append("-C")
            git.append(self.dir)
        git.append(cmd)
        git.extend(args)
        return processRun(git)

    def pull(self, *args):
        return self.run('pull', *args)

    def checkout(self, *args):
        self.run('checkout', *args)
        self.run('submodule', 'update')

    def getCommitHash(self, commit):
        return self.run('rev-parse', commit).rstrip()

    def getCommitTime(self, commit):
        return int(self.run('show', '-s', '--format=%ct', commit).strip())

    def getNextCommitHash(self, commit):
        commits = self.run('rev-list', '--reverse', commit+"..HEAD").strip().split('\n')
        next_commit = commits[0].strip()
        return next_commit if len(next_commit) > 0 else commit
