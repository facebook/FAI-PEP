#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2022-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


from typing import Any

from platforms.android.adb import ADB
from platforms.ios.idb import IDB

from utils.custom_logger import getLogger


def getBatteryState(device, platform: str, android_dir: str) -> dict[str, Any]:
    state: dict[str, Any] = {
        "supported": False,
        "disconnected": None,
        "status": None,
        "charge_level": None,
        "temperature": None,
    }
    try:
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
    except Exception:
        # If error occured, change supported state to false to allow
        # downstream logic not to examine individual fields.
        state["supported"] = False
        getLogger().exception("Failed to get battery state")

    return state
