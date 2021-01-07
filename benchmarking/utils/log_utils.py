#!/usr/bin/env python

##############################################################################
# Copyright 2019-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from utils.custom_logger import getLogger

LOG_LIMIT = 16 * (10**6)
DEFAULT_INTERVAL=10
MINIMUM_INTERVAL=5

def valid_interval(arg) -> int:
    try:
        value = int(arg)
        if value < MINIMUM_INTERVAL:
            raise ValueError()
    except ValueError:
        getLogger().warning("Logging interval must be specified as an integer in seconds >= {}.  Using default {}s.".format(MINIMUM_INTERVAL,DEFAULT_INTERVAL))
        value = DEFAULT_INTERVAL
    return value

def trimLog(output):
    if sys.getsizeof(output) > LOG_LIMIT:
        getLogger().error("Error, output is too large")
        output = output[-LOG_LIMIT:]
    return output

def collectLogData(job):
    res = None
    if job["framework"] == "generic":
        if "control" not in job["benchmarks"]["info"]:
            res = _block_from_log(
                job["log"], "Program Output:", "=" * 80)
            res = "\n".join(["=" * 80] + res) if res else None
        else:
            res = None
            res1 = _block_from_log(
                job["log"], "Program Output:", "=" * 80)
            res2 = _block_from_log(
                job["log"], "Program Output:", "=" * 80, False)
            if res1 and res2:
                res1[0] = "After the change, Program Output:"
                res2[0] = "Before the change, Program Output:"
                res = "\n".join(["=" * 80] + res2 + res1)
    return res or job["log"] or "Logs unavailable."

def _block_from_log(log, s1, s2, forward=True):
    start, end, first = None, None, True
    temp = log.split("\n")
    if forward:
        for i, s in enumerate(temp):
            if s1 == s:
                start = i
            if s2 == s:
                if first:
                    first = False
                else:
                    end = i
            if start and end:
                return temp[start:end + 1]
    else:
        for i, s in enumerate(temp[::-1]):
            if s1 == s:
                start = len(temp) - 1 - i
            if s2 == s and not end:
                end = len(temp) - 1 - i
            if start and end:
                return temp[start:end + 1]
    return None
