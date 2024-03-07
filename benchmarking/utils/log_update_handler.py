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

import logging
import sys
import threading
import time

from bridge.db import DBDriver
from utils.custom_logger import getLogger
from utils.log_utils import DEFAULT_INTERVAL, LOG_LIMIT, trimLog


class DBLogUpdateHandler(logging.Handler):
    """
    Handler class to write log data to DB at regular intervals.
    """

    def __init__(
        self, db: DBDriver, id: int, interval: float = DEFAULT_INTERVAL, retries=3
    ):
        """
        Initialize the handler.
        If stream is not specified, sys.stderr is used.
        """
        logging.Handler.__init__(self)
        self.db = db
        self.id = id
        self.interval = interval
        self.retries = retries
        self.retries_left = self.retries
        self.lastreq = 0
        self.log = []
        self.running = True
        self.dbLoggingThread = threading.Thread(target=self.startLogging)
        self.dbLoggingThread.start()

    def emit(self, record):
        """
        Emit a record.
        Handler formatting
        Append to log buffer
        """
        msg = self.format(record)
        self.log.append(msg)

    def startLogging(self):
        while self.running:
            if self.log and time.time() >= self.lastreq + self.interval:
                try:
                    output = "\n".join(self.log)
                    if sys.getsizeof(output) > LOG_LIMIT:
                        self.running = False
                        output = trimLog(output)
                    else:
                        self.log = [output]
                    status = self.db.updateLogBenchmarks(self.id, output)
                    if status != "success":
                        getLogger().error("Error updating logs.")
                        self.retries_left -= 1
                        if self.retries_left == 0:
                            self.running = False
                            getLogger().critical(
                                "Max failed attempts reached for log updates. Stopping log update requests."
                            )
                    else:
                        self.retries_left = self.retries
                    self.lastreq = time.time()
                except Exception:
                    getLogger().exception("Error occurred in realtime logging loop.")
                    self.running = False
            time.sleep(1)

    def close(self):
        self.running = False
        super().close()
