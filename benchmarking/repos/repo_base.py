#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import abc


class RepoBase:
    def __init__(self, dir):
        self.dir = dir

    @abc.abstractmethod
    def pull(self, *args):
        pass

    @abc.abstractmethod
    def checkout(self, *args):
        pass

    @abc.abstractmethod
    def getCommitHash(self, commit):
        pass

    @abc.abstractmethod
    def getCommitTime(self, commit):
        pass

    @abc.abstractmethod
    def getNextCommitHash(self, commit):
        pass

    @abc.abstractmethod
    def getCommitsInRange(self, start_date, end_date):
        pass

    @abc.abstractmethod
    def getPriorCommits(self, commit, num):
        pass
