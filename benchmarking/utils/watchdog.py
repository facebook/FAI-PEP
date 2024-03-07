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

import threading
import time


class WatchDog:
    def __init__(self, main, condition, action, delay=15.0, once=True):
        self.main = main
        self.condition = condition
        self.action = action
        self.delay = delay
        self.once = once

        self.running = False
        self.watchdog = None

    def __call__(self, *args):
        return self.start(*args)

    def start(self, *args):
        self.running = True
        self._startWatchdog()
        ret = self.main(*args)
        self.running = False
        self.watchdog.join()
        return ret

    def _startWatchdog(self):
        self.watchdog = threading.Thread(target=self._runWatchdog)
        self.watchdog.start()

    def _runWatchdog(self):
        while self.running:
            triggered = self.condition()
            if triggered:
                self.action()
                if self.once:
                    break
            time.sleep(self.delay)
