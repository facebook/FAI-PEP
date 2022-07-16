#!/usr/bin/env python

##############################################################################
# Copyright 2022-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

from typing import Any, Dict

from platforms.android.adb import ADB
from platforms.ios.idb import IDB


def getBatteryState(device, platform: str, android_dir: str) -> Dict[str, Any]:
    state: Dict[str, Any] = {"supported": False}
    if platform.startswith("ios"):
        util = IDB(device)
        return state  # NYI
    elif platform.startswith("android"):
        util = ADB(device, android_dir)
        if util.isRootedDevice():
            if not util.user_is_root():
                util.root(silent=True)
            state["supported"] = util.getBatteryProp("present") == "1"

        if state["supported"]:
            state["disconnected"] = util.getBatteryProp("input_suspend") == "1"
            state["status"] = util.getBatteryProp("status")
            state["charge_level"] = int(util.getBatteryProp("capacity"))
            state["temperature"] = int(util.getBatteryProp("temp"))

    return state
