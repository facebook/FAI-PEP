#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import json
from six import string_types

from platforms.android.adb import ADB
from platforms.android.android_platform import AndroidPlatform
from utils.arg_parse import getArgs
from utils.custom_logger import getLogger


class AndroidDriver:
    def __init__(self, devices=None):
        if devices:
            if isinstance(devices, string_types):
                devices = [devices]
        self.devices = devices
        self.type = "android"
        self.hash_platform_mapping = None
        if getArgs().hash_platform_mapping:
            try:
                with open(getArgs().hash_platform_mapping) as f:
                    self.hash_platform_mapping = json.load(f)
            except OSError as e:
                getLogger().info("OSError: {}".format(e))
            except ValueError as e:
                getLogger().info('Invalid json: {}'.format(e))

    def getDevices(self):
        adb = ADB()
        devices_str = adb.run("devices", "-l")
        rows = devices_str.split('\n')
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
        if getArgs().device:
            device = None
            device_str = getArgs().device
            if device_str[0] == '{':
                device = json.loads(device_str)
                hash = device["hash"]
            else:
                hash = getArgs().device
            adb = ADB(hash)
            platform = self.getAndroidPlatform(tempdir, adb)
            platforms.append(platform)
            if device:
                platform.setPlatform(device["kind"])
            return platforms

        if self.devices is None:
            self.devices = self.getDevices()
        if getArgs().excluded_devices:
            excluded_devices = \
                set(getArgs().excluded_devices.strip().split(','))
            self.devices = self.devices.difference(excluded_devices)

        if getArgs().devices:
            supported_devices = set(getArgs().devices.strip().split(','))
            if supported_devices.issubset(self.devices):
                self.devices = supported_devices

        for device in self.devices:
            adb = ADB(device)
            platforms.append(self.getAndroidPlatform(tempdir, adb))
        return platforms

    def getAndroidPlatform(self, tempdir, adb):
        platform = AndroidPlatform(tempdir, adb)
        if self.hash_platform_mapping and \
            platform.platform_hash in self.hash_platform_mapping:
            platform.platform = \
                self.hash_platform_mapping[platform.platform_hash]
        return platform
