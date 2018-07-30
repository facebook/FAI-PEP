#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import abc


class DataConverterBase(object):
    def __init__(self):
        pass

    @abc.abstractmethod
    def getName(self):
        return "Error"

    # collect data from the binary
    @abc.abstractmethod
    def collect(self, data, identifier):
        assert False, "Need to call one of " + \
            "the implementations of the collector"

    # convert the data to a unified format
    @abc.abstractmethod
    def convert(self, data):
        assert False, "Need to call one of " + \
            "the implementations of the converter"
