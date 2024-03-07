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

from utils.subprocess_with_logger import processRun


class PlatformUtilBase:
    def __init__(self, device=None, tempdir=None):
        self.device = device
        self.tempdir = tempdir

    def run(self, *args, **kwargs):
        cmd = self._prepareCMD(*args)
        return processRun(cmd, **kwargs)[0]

    @abc.abstractmethod
    def push(self, src, tgt):
        raise AssertionError("Push method must be derived")

    @abc.abstractmethod
    def pull(self, src, tgt):
        raise AssertionError("Pull method must be derived")

    @abc.abstractmethod
    def deleteFile(self, file):
        raise AssertionError("Delete file method must be derived")

    def _prepareCMD(self, *args):
        cmd = []
        for item in args:
            if isinstance(item, list):
                cmd.extend(item)
            else:
                cmd.append(item)
        return cmd
