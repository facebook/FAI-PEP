#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


class RegressionDetectorBase:
    def __init__(self):
        pass

    def isRegressed(self, filename, latest_data, compare_data, control_in_compare):
        return None
