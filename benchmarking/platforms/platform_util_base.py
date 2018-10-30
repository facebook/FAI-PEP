#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import abc

from utils.subprocess_with_logger import processRun


class PlatformUtilBase(object):
    def __init__(self, device=None, tempdir=None):
        self.device = device
        self.tempdir = tempdir

    def run(self, *args, **kwargs):
        cmd = []
        for item in args:
            if isinstance(item, list):
                cmd.extend(item)
            else:
                cmd.append(item)

        return processRun(cmd, **kwargs)[0]

    @abc.abstractmethod
    def push(self, src, tgt):
        assert False, "Push method must be derived"

    @abc.abstractmethod
    def pull(self, src, tgt):
        assert False, "Pull method must be derived"

    @abc.abstractmethod
    def deleteFile(self, file):
        assert False, "Delete file method must be derived"
