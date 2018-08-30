#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import logging
import sys

FORMAT = '%(levelname)s %(asctime)s %(filename)s:%(lineno)4d: %(message)s'
logging.basicConfig(level=logging.DEBUG, format=FORMAT,
                    datefmt="%H:%M:%S", stream=sys.stdout)
logger = logging.getLogger("GlobalLogger")


def getLogger():
    return logger
