#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import argparse

args = None
unknowns = []
parser = argparse.ArgumentParser(description="Perform one benchmark run")


def getParser():
    return parser


def parse():
    global args
    args = parser.parse_args()
    return args


def parseKnown():
    global args, unknowns
    args, unknowns = parser.parse_known_args()
    return args


def getArgs():
    return args


def getUnknowns():
    return unknowns
