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
import abc
from six import string_types


class DataConverterBase(object):
    def __init__(self):
        pass

    @abc.abstractmethod
    def getName(self):
        return "Error"

    # collect data from the binary
    @abc.abstractmethod
    def collect(self, data, args):
        assert False, "Need to call one of " + \
            "the implementations of the collector"

    # convert the data to a unified format
    @abc.abstractmethod
    def convert(self, data):
        assert False, "Need to call one of " + \
            "the implementations of the converter"

    def _prepareData(self, data):
        if data is None:
            return []
        if isinstance(data, string_types):
            rows = data.split('\n')
        else:
            assert isinstance(data, list), \
                "Input format must be string or list"
            rows = data
        return rows
