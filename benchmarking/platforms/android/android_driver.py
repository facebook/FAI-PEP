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
import json
from six import string_types

from platforms.android.adb import ADB
from platforms.android.android_platform import AndroidPlatform


class AndroidDriver:
    def __init__(self, args, devices=None):
        self.args = args
        if devices:
            if isinstance(devices, string_types):
                devices = [devices]
        self.devices = devices
        self.type = "android"

    def getDevices(self):
        adb = ADB()
        rows = adb.run("devices", "-l")
        rows.pop(0)
        devices = set()
        for row in rows:
            items = row.strip().split(' ')
            if len(items) > 2 and "device" in items:
                device_id = items[0].strip()
                devices.add(device_id)
        return devices

    def getAndroidPlatforms(self, tempdir):
        platforms = []
        if self.args.device:
            device = None
            device_str = self.args.device
            if device_str[0] == '{':
                device = json.loads(device_str)
                hash = device["hash"]
            else:
                hash = self.args.device
            adb = ADB(hash, tempdir)
            platform = AndroidPlatform(tempdir, adb, self.args)
            platforms.append(platform)
            if device:
                platform.setPlatform(device["kind"])
            return platforms

        if self.devices is None:
            self.devices = self.getDevices()
        if self.args.excluded_devices:
            excluded_devices = \
                set(self.args.excluded_devices.strip().split(','))
            self.devices = self.devices.difference(excluded_devices)

        if self.args.devices:
            supported_devices = set(self.args.devices.strip().split(','))
            if supported_devices.issubset(self.devices):
                self.devices = supported_devices

        for device in self.devices:
            adb = ADB(device, tempdir)
            platforms.append(AndroidPlatform(tempdir, adb, self.args))
        return platforms
