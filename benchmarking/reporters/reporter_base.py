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


class ReporterBase(object):
    DATA = "data"
    META = "meta"
    PLATFORM = "platform"

    def __init__(self):
        pass

    def report(self, content):
        pass
