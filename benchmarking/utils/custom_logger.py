#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import logging
logging.basicConfig()

logger = logging.getLogger("GlobalLogger")

logger.setLevel(logging.DEBUG)


def getLogger():
    return logger
