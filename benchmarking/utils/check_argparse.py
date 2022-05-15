#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


from __future__ import absolute_import, division, print_function, unicode_literals

import argparse


def claimer_id_type(claimer_id):
    if len(claimer_id) > 40:
        raise argparse.ArgumentTypeError(
            "The length of claimer_id should be " "less than 40"
        )
    return claimer_id
