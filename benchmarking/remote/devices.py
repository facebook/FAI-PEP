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

import copy
import json
import os

from utils.devices import devices as devices_dict


class Devices:
    def __init__(self, filename=None):
        if filename:
            # if the user provides filename, we will load it.
            assert os.path.isfile(filename), "Device file {} does not exist".format(
                filename
            )
            with open(filename, "r") as f:
                self.devices = json.load(f)
        else:
            # otherwise read from internal
            self.devices = copy.deepcopy(devices_dict)
        self._elaborateDevices()

    def getFullNames(self, devices):
        names = devices.split(",")
        new_names = [
            self.devices[name]["name"] if name in self.devices else name
            for name in names
        ]
        return ",".join(new_names)

    def getAbbrs(self, abbr):
        if abbr in self.devices:
            device = self.devices[abbr]
            if "abbr" in device:
                return device["abbr"]
        return None

    def _elaborateDevices(self):
        device_abbr = []
        for name, _ in self.devices.items():
            device = self.devices[name]
            assert "name" in device, "Field name is required in devices"
            assert device["name"] == name, (
                "Device key ({}) and name ({})".format(name, device["name"])
                + " do not match"
            )
            if "abbr" in device:
                assert isinstance(
                    device["abbr"], list
                ), "Abbreviations for {} needs to be a list".format(name)
                for abbr in device["abbr"]:
                    device_abbr.append((device, abbr))

        for device_abbr_pair in device_abbr:
            self._elaborateOneDevice(device_abbr_pair[0], device_abbr_pair[1])

    def _elaborateOneDevice(self, device, abbr):
        assert abbr not in self.devices, (
            "Abbreviation " + "{} is already specified in the device list".format(abbr)
        )
        self.devices[abbr] = device
