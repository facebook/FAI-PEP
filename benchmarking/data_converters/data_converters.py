#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


converters = {}


def registerConverter(converter):
    converters[converter.getName()] = converter


def getConverters():
    global converters
    return converters
