#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


import abc


class DataConverterBase:
    def __init__(self):
        pass

    @staticmethod
    def getName():
        return "Error"

    # collect data from the binary
    @abc.abstractmethod
    def collect(self, data, args):
        raise AssertionError("Need to call one of the implementations of the collector")

    # convert the data to a unified format
    @abc.abstractmethod
    def convert(self, data):
        raise AssertionError("Need to call one of the implementations of the converter")

    def _prepareData(self, data):
        if data is None:
            return []
        if isinstance(data, str):
            rows = data.split("\n")
        else:
            assert isinstance(data, list), "Input format must be string or list"
            rows = data
        return rows
