#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


profilers = {}
profilersByUsage = {}


def registerProfiler(name, profiler, usage=None):
    global profilers
    global profilersByUsage
    profilers[name] = profiler
    if usage:
        profilersByUsage[usage] = profiler


def getProfiler(name, id=None):
    global profilers
    if name not in profilers:
        return None
    return profilers[name](id)


def getProfilerByUsage(usage, id=None):
    global profilersByUsage
    if usage not in profilersByUsage:
        return None
    return profilersByUsage[usage](id)
