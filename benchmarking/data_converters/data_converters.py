#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


from .json_data_converter.json_data_converter import JsonDataConverter

converters = {
    "json_data_converter": JsonDataConverter,
}


def getConverters():
    global converters
    return converters
