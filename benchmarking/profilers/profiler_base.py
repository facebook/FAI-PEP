#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2019-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import abc

from utils.future import Future


class ProfilerBase:
    def __init__(self, id=None):
        self.id = id

    def start(self, **kwargs):
        f = Future(self._start)
        f.start(self.id, **kwargs)
        return f

    @abc.abstractmethod
    def _start(self, id, **kwargs):
        return None

    def getId(self, f):
        return f.result()
