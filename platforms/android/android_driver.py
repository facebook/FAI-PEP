#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from platforms.android.adb import ADB
from platforms.android.android_platform import AndroidPlatform
from utils.arg_parse import getArgs, getParser

getParser().add_argument("--android", action="store_true",
    help="Run the benchmark on all connected android devices.")

class AndroidDriver:
    def __init__(self, devices = None):
        self.adb = ADB()
        if devices:
            if isinstance(devices, string):
                devices = [devices]
        self.devices = devices

    def getDevices(self):
        devices_str = self.adb.run("devices", "-l")
        rows = devices_str.split('\n')
        rows.pop(0)
        devices = []
        for row in rows:
            items = row.strip().split(' ')
            if len(items) > 2 and "device" in items:
                device_id = items[0].strip()
                devices.append(device_id)
        return devices


    def getAndroidPlatforms(self):
        if self.devices is None:
            self.devices = self.getDevices()
        platforms = []
        for device in self.devices:
            adb = ADB(device)
            platforms.append(AndroidPlatform(adb))
        return platforms
