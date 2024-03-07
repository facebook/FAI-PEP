#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

from data_converters.data_converter_base import DataConverterBase
from data_converters.data_converters import registerConverter
from data_converters.json_converter.json_converter import JsonConverter


class JsonWithIdentifierConverter(DataConverterBase):
    def __init__(self):
        self.json_converter = JsonConverter()

    @staticmethod
    def getName():
        return "json_with_identifier_converter"

    def collect(self, data, args=None):
        rows = self._prepareData(data)
        identifier = None
        if args and "identifier" in args:
            identifier = args["identifier"]
        useful_rows = (
            [
                row[(row.find(identifier) + len(identifier)) :]
                for row in rows
                if row.find(identifier) >= 0
            ]
            if identifier
            else rows
        )
        return self.json_converter.collect(useful_rows)

    def convert(self, data):
        return self.json_converter.convert(data)


registerConverter(JsonWithIdentifierConverter)
