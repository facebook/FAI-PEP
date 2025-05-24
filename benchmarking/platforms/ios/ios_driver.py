#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


import json
import re

from platforms.driver_base import DriverBase, registerDriver

from platforms.ios.idb import IDB
from platforms.ios.ios_platform import IOSPlatform
from platforms.ios.xcrun import xcrun


class IOSDriver(DriverBase):
    def __init__(self, args, devices=None):
        self.args = args
        self.devices = self.getDevices()
        if devices:
            if isinstance(devices, str):
                devices = [devices]
            self.devices = {d: self.devices[d] for d in self.devices if d in devices}
        self.type = "ios"

    def getDevices(self, silent=True, retry=1):
        idb = IDB()
        rows = idb.run(["--detect", "--timeout", "1"], silent=silent, retry=1)
        if len(rows) == 0:
            return {}
        rows.pop(0)
        pattern = re.compile(
            r".* Found ([\d|a-f|\-|A-F]+) \((\w+), .+, .+, (.+), (.+), .+\) a\.k\.a\. .*"
        )
        devices = {}
        for row in rows:
            match = pattern.match(row)
            if match:
                hash = match.group(1)
                model = match.group(2)
                abi = match.group(3)
                os_version = match.group(4)
                devices[hash] = {"model": model, "abi": abi, "os_version": os_version}
        return devices

    def getPlatforms(self, tempdir, usb_controller):
        platforms = []
        if self.args.device:
            device_str = self.args.device
            assert device_str[0] == "{", "device must be a json string"
            device = json.loads(device_str)
            hash = device["hash"]
            platform_meta = {
                "os_version": self.devices[hash]["os_version"],
                "model": self.devices[hash]["model"],
                "abi": self.devices[hash]["abi"],
            }
            os_major_version = int(platform_meta.get("os_version", None).split(".")[0])
            platform_util = (
                IDB(hash, tempdir) if os_major_version < 17 else xcrun(hash, tempdir)
            )
            platform = IOSPlatform(
                tempdir, platform_util, self.args, platform_meta, usb_controller
            )
            platform.setPlatform(self.devices[hash]["model"])
            platforms.append(platform)
            return platforms

        if self.args.excluded_devices:
            self.devices = {
                d: self.devices[d]
                for d in self.devices
                if d not in self.args.excluded_devices
            }

        if self.args.devices:
            self.devices = {
                d: self.devices[d] for d in self.devices if d in self.args.devices
            }

        for device in self.devices:
            platform_meta = {
                "os_version": self.devices[device]["os_version"],
                "model": self.devices[device]["model"],
                "abi": self.devices[device]["abi"],
            }
            os_major_version = int(platform_meta.get("os_version", None).split(".")[0])
            platform_util = (
                IDB(device, tempdir)
                if os_major_version < 17
                else xcrun(device, tempdir)
            )
            platform = IOSPlatform(tempdir, platform_util, self.args, platform_meta)
            # platform.setPlatform(self.devices[device]["platform"])
            platforms.append(platform)

        return platforms

    @staticmethod
    def matchPlatformArgs(args):
        return args.platform.startswith("ios")


registerDriver("IOSDriver", IOSDriver)
