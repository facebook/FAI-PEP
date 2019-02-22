#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals
import logging
import sys

FORMAT = '%(levelname)s %(asctime)s %(filename)s:%(lineno)4d: %(message)s'
logging.basicConfig(level=logging.DEBUG, format=FORMAT,
                    datefmt="%H:%M:%S", stream=sys.stdout)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logger = logging.getLogger("GlobalLogger")


def getLogger():
    return logger


def setLoggerLevel(level):
    if level == "info":
        logger.setLevel(logging.INFO)
    elif level == "warning":
        logger.setLevel(logging.WARNING)
    elif level == "error":
        logger.setLevel(logging.ERROR)
