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
import argparse

from platforms.android.adb import ADB
from platforms.ios.idb import IDB

parser = argparse.ArgumentParser()
parser.add_argument("--android_dir", default="/data/local/tmp/",
    help="The directory in the android device all files are pushed to.")
parser.add_argument("--device", required=True,
    help="Specify the device hash to reboot")
parser.add_argument("-p", "--platform", required=True,
    help="Specify the platform to benchmark on. "
        "Must starts with ios or android")


def reboot(**kwargs):
    raw_args = kwargs.get("raw_args", None)
    args, _ = parser.parse_known_args(raw_args)
    device = args.device
    platform = args.platform
    if platform.startswith("ios"):
        util = IDB(device)
    elif platform.startswith("android"):
        util = ADB(device, args.android_dir)
    else:
        assert False, "Platform {} not recognized".format(platform)
    util.reboot()
    print("Reboot Success")


if __name__ == "__main__":
    reboot()
