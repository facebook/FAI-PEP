#!/usr/bin/env python

##############################################################################
# Copyright 2019-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import threading


# Future provides a simple way for callers to asyncronously run a function
# and later retrieve the result. Using a normal bool to indicate if the
# function has finished is safe due to python's GIL. We don't need any
# special atomic operations.


class Future(object):
    def __init__(self, func):
        self.func = func
        self.thread = None
        self.retval = None
        self.finished = False
        self.joined = False

    def start(self, *args, **kwargs):
        self.thread = threading.Thread(
            target=self._runAndCapture, args=args, kwargs=kwargs
        )
        self.thread.start()

    def result(self):
        if self.joined:
            return self.retval
        self.thread.join()
        self.joined = True
        return self.retval

    def isFinished(self):
        return self.finished

    def _runAndCapture(self, *args, **kwargs):
        self.retval = self.func(*args, **kwargs)
        self.finished = True
