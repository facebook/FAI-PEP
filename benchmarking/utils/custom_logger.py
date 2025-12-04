#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


import logging
import os
import sys

LOGFILE = os.getenv("AIBENCH_LOGFILE")
FORMAT = "%(levelname)s %(asctime)s %(filename)s:%(lineno)4d: %(message)s"
if LOGFILE is not None:
    logging.basicConfig(
        level=logging.DEBUG,
        format=FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
        filename=LOGFILE,
    )
else:
    logging.basicConfig(
        level=logging.DEBUG,
        format=FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logger = logging.getLogger("GlobalLogger")

# Check for AIBENCH_LOGGER_LEVEL environment variable to set initial log level
# This allows setting log level before any code runs via environment variable
_initial_level = os.getenv("AIBENCH_LOGGER_LEVEL", "info").lower()
if _initial_level == "debug":
    logger.setLevel(logging.DEBUG)
elif _initial_level == "info":
    logger.setLevel(logging.INFO)
elif _initial_level == "warning":
    logger.setLevel(logging.WARNING)
elif _initial_level == "error":
    logger.setLevel(logging.ERROR)
else:
    logger.setLevel(logging.INFO)  # Default to INFO


def getLogger():
    return logger


def setLoggerLevel(level):
    if level == "debug":
        logger.setLevel(logging.DEBUG)
    elif level == "info":
        logger.setLevel(logging.INFO)
    elif level == "warning":
        logger.setLevel(logging.WARNING)
    elif level == "error":
        logger.setLevel(logging.ERROR)
