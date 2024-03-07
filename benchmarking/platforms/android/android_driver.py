#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import json

from platforms.android.adb import ADB
from platforms.android.android_platform import AndroidPlatform

from platforms.driver_base import DriverBase, registerDriver

from six import string_types


class AndroidDriver(DriverBase):
    def __init__(self, args, devices=None):
        self.args = args
        if devices:
            if isinstance(devices, string_types):
                devices = [devices]
        self.devices = devices
        self.type = "android"

    @staticmethod
    def matchPlatformArg(*args):
        return args.platform[:7] == "android"

    def getDevices(self, silent=False, retry=1):
        adb = ADB()
        rows = adb.run("devices", "-l", silent=silent, retry=1)
        rows.pop(0)
        devices = set()
        for row in rows:
            items = row.strip().split()
            if len(items) > 2 and "device" in items:
                device_id = items[0].strip()
                devices.add(device_id)
        return devices

    def getPlatforms(self, tempdir, usb_controller):
        platforms = []
        if self.args.device:
            device = None
            device_str = self.args.device
            if device_str[0] == "{":
                device = json.loads(device_str)
                hash = device["hash"]
            else:
                hash = self.args.device
            adb = ADB(hash, tempdir)
            platform = AndroidPlatform(tempdir, adb, self.args, usb_controller)
            platforms.append(platform)
            if device:
                platform.setPlatform(device["kind"])
            return platforms

        if self.devices is None:
            self.devices = self.getDevices()
        if self.args.excluded_devices:
            excluded_devices = set(self.args.excluded_devices.strip().split(","))
            self.devices = self.devices.difference(excluded_devices)

        if self.args.devices:
            supported_devices = set(self.args.devices.strip().split(","))
            if supported_devices.issubset(self.devices):
                self.devices = supported_devices

        for device in self.devices:
            adb = ADB(device, tempdir)
            platforms.append(AndroidPlatform(tempdir, adb, self.args))
        return platforms

    @staticmethod
    def matchPlatformArgs(args):
        return args.platform[:7] == "android"


registerDriver("AndroidDriver", AndroidDriver)
