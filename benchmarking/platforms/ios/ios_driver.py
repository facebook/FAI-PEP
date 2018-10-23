#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import json
import re
from six import string_types

from platforms.ios.idb import IDB
from platforms.ios.ios_platform import IOSPlatform
from utils.arg_parse import getArgs


class IOSDriver(object):
    def __init__(self, devices=None):
        if devices:
            if isinstance(devices, string_types):
                devices = [devices]
        self.devices = devices
        self.type = "ios"

    def getDevices(self):
        idb = IDB()
        devices_str = idb.run("--detect")
        if devices_str is None:
            return {}
        rows = devices_str.split('\n')
        rows.pop(0)
        pattern = re.compile(".* Found ([\d|a-f]+) \((\w+), .+\) a\.k\.a\. .*")
        devices = {}
        for row in rows:
            match = pattern.match(row)
            if match:
                hash = match.group(1)
                model = match.group(2)
                devices[hash] = model
        return devices

    def getIOSPlatforms(self, tempdir):
        platforms = []
        if getArgs().device:
            device_str = getArgs().device
            assert device_str[0] == '{', "device must be a json string"
            device = json.loads(device_str)
            idb = IDB(device["hash"], tempdir)
            platform = IOSPlatform(tempdir, idb)
            platform.setPlatform(device["kind"])
            platforms.append(platform)
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
            model = self.devices[device]
            idb = IDB(device, tempdir)
            platform = IOSPlatform(tempdir, idb)
            platform.setPlatform(model)
            platforms.append(platform)

        return platforms
