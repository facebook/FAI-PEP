#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from platforms.android.adb import ADB
from platforms.ios.idb import IDB


from utils.arg_parse import getParser, getArgs, parse

getParser().add_argument("--device", required=True,
    help="Specify the device hash to reboot")

getParser().add_argument("-p", "--platform", required=True,
    help="Specify the platform to benchmark on. "
        "Must starts with ios or android")


def reboot():
    parse()
    device = getArgs().device
    platform = getArgs().platform
    if platform.startswith("ios"):
        util = IDB(device)
    elif platform.startswith("android"):
        util = ADB(device)
    else:
        assert False, "Platform {} not recognized".format(platform)
    util.reboot()
    print("Reboot Success")


if __name__ == "__main__":
    reboot()
