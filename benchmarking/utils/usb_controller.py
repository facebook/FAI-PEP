##############################################################################
# Copyright 2020-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

# pyre-unsafe

import json
import multiprocessing

import brainstem
from brainstem.result import Result
from utils.custom_logger import getLogger


manager = multiprocessing.Manager()


class USBController:
    """Controller for Acroname USB hubs. This class will allow lab devices
    to be connected and disconnected from the lab by their device meta data.

    loaded with mapping:
    {
        "hub_serial": {
            "port_number": "device_hash"
        }
    }
    """

    def __init__(self, usb_hub_device_mapping):
        self.device_map = {}  # map of device hash to (hub_serial, port_num)
        self.active = manager.dict()  # device hash to enable/disable boolean status

        with open(usb_hub_device_mapping) as f:
            mapping = json.load(f)

        getLogger().info("mapping {}".format(mapping))
        for hub_serial, port_device_map in mapping.items():
            for port_number, device_hash in port_device_map.items():
                self.device_map[device_hash] = (int(port_number), hub_serial)
                self.active[device_hash] = True  # default on
        getLogger().info("mapping {}".format(self.device_map))

    def connect(self, device_hash):
        try:
            port_number, hub_serial = self.device_map[device_hash]
        except KeyError:
            raise Exception("Device {} or hub not connected".format(device_hash))

        stem = brainstem.stem.USBHub3p()
        result = stem.discoverAndConnect(brainstem.link.Spec.USB, int(hub_serial))

        if result != Result.NO_ERROR:
            raise Exception(
                "Could not connect to hub {} with error code {}".format(
                    hub_serial, result
                )
            )

        try:
            result = stem.usb.setPortEnable(port_number)
            if result == Result.NO_ERROR:
                self.active[device_hash] = True
            else:
                raise Exception(
                    "Could not enable port {} with error code {}".format(
                        port_number, result
                    )
                )
        finally:
            stem.disconnect()

    def disconnect(self, device_hash):
        try:
            port_number, hub_serial = self.device_map[device_hash]
        except KeyError:
            raise Exception("Device {} or hub not connected".format(device_hash))

        stem = brainstem.stem.USBHub3p()
        result = stem.discoverAndConnect(brainstem.link.Spec.USB, int(hub_serial))

        if result != Result.NO_ERROR:
            raise Exception(
                "Could not connect to hub {} with error code {}".format(
                    hub_serial, result
                )
            )

        try:
            result = stem.usb.setPortDisable(port_number)
            if result == Result.NO_ERROR:
                self.active[device_hash] = False
            else:
                raise Exception(
                    "Could not diable port {} with error code {}".format(
                        port_number, result
                    )
                )
        finally:
            stem.disconnect()
