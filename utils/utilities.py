#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import datetime


def getDirectory(commit_hash, commit_time):
    dt = datetime.datetime.fromtimestamp(
        commit_time, datetime.timezone.utc)
    directory = str(dt.year) + "/" + \
        str(dt.month) + "/" + \
        str(dt.day) + "/" + \
        commit_hash + "/"
    return directory
