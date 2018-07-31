#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


from .json_converter.json_converter import JsonConverter
from .json_with_identifier_converter.json_with_identifier_converter \
    import JsonWithIdentifierConverter

converters = {
    "json_converter": JsonConverter,
    "json_with_identifier_converter": JsonWithIdentifierConverter,
}


def getConverters():
    global converters
    return converters
