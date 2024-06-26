##############################################################################
# Copyright 2020-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

# pyre-unsafe

import json
import platform
import re
import subprocess

from utils.custom_logger import getLogger
from utils.usb_controller_base import USBControllerBase


class AcronameUSBController(USBControllerBase):
    """
    Controller for Acroname USB hubs. This leverages the Brainstem SDK published by Acroname to control the
    hubs. We use the Brainstem CLI (the AcronameHubCLI and Updater command line tools) provided with the
    Brainstem SDK available at https://acroname.com/software/brainstem-development-kit
    """

    def __init__(self, hub_map=None):
        getLogger().info("Initializing AcronameUSBController Hub Map")
        self.active = {}
        self.device_map = (
            (
                self._construct_device_map_macos()
                if platform.system() == "Darwin"
                else {}
            )
            if hub_map is None
            else self._load_device_map(hub_map)
        )

    def connect(self, device_hash):
        listing = self.device_map.get(device_hash)
        if listing is None:
            getLogger().error(
                "Could not find hub serial for device {}".format(device_hash)
            )
            return []
        self.active[device_hash] = True
        return self._cli_toggle_port(
            listing.get("hub_serial"), str(listing.get("port_number")), 1
        )

    def disconnect(self, device_hash):
        listing = self.device_map.get(device_hash)
        if listing is None:
            getLogger().error(
                "Could not find hub serial for device {}".format(device_hash)
            )
            return []

        self.active[device_hash] = False
        return self._cli_toggle_port(
            listing.get("hub_serial"), str(listing.get("port_number")), 0
        )

    """
    Uses the AcronameHubCLI to toggle the ports on or off where needed.

    Parameters:
        hub_serial (str): Serial ID of the Acroname hub
        port_number (str): Port number(s) of the device connected to the hub Note that this can be a single number
            or a comma-separated list of numbers. For example, "1" or "1,3" as per the CLI tool.    

    Returns:
        devices (list): List of Device objects filtered by given status parameter
    """

    @staticmethod
    def _cli_toggle_port(hub_serial, port_number: str, enable: int):
        args = [
            "AcronameHubCLI",
            "-s",
            str(hub_serial),
            "-p",
            port_number,
            "-e",
            str(enable),
        ]
        return subprocess.check_output(args)

    """
    Automatically attempts to resolve the mapping of device hashes to hubs and ports.

    This specifically uses MacOS' systemprofiler to discover USB hubs and the devices connected to them.
    """

    def _construct_device_map_macos(self):
        getLogger().info("Constructing device mapping")
        # Get a hierarchical JSON of all of the USB-type devices
        sp_output = subprocess.check_output(
            ["system_profiler", "SPUSBDataType", "-json"]
        )
        sp_items = json.loads(sp_output).get("SPUSBDataType")
        getLogger().info("sp_items")

        # Recursively find the items in this listing that represent our hubs.
        def _extract_hubs_from_items(items_list):
            hubs = []
            for item in items_list:
                if (
                    "USBHub" in item.get("_name")
                    and "Acroname" in item.get("manufacturer")
                    and re.search(r"\[([0-9])-(?:[0-9])+\]", item.get("_name"))
                    is not None
                ):
                    getLogger().info(f"Found hub {item}")
                    hubs.append(item)
                else:
                    hubs.extend(_extract_hubs_from_items(item.get("_items", [])))
            return hubs

        hubs = list(_extract_hubs_from_items(sp_items))

        self.device_map = {}

        for hub in hubs:
            # Ensure all ports are enabled. If the server has crashed previously, it's possible these aren't in a good state.
            self._cli_toggle_port(
                hub.get("serial_num"), ",".join([str(i) for i in range(0, 8)]), 1
            )

        # Refresh our system_profiler output now that we may have new devices connected to the hubs.
        sp_output = subprocess.check_output(
            ["system_profiler", "SPUSBDataType", "-json"]
        )
        sp_items = json.loads(sp_output).get("SPUSBDataType")
        hubs = list(_extract_hubs_from_items(sp_items))

        for hub in hubs:
            for device in hub.get("_items", []):
                getLogger().info(f"Device {device}")
                device_hash = device.get("serial_num")
                port_number = self._resolve_port_number(
                    hub.get("_name"), device.get("location_id")
                )
                hub_serial = hub.get("serial_num")
                self.device_map[device_hash] = {
                    "hub_serial": hub_serial,
                    "port_number": port_number,
                }
                self.active[device_hash] = True

        getLogger().info("Hub Mapping {}".format(self.device_map))

    def _load_device_map(self, device_map_filepath):
        with open(device_map_filepath, "r") as f:
            self.device_map = json.load(f)

    """
    Hubs with more than 4 ports are represented as separate devices. For example, an 8-port hub
    will have two listings formatted like "USBHub3p-2[0-3]" and "USBHub3p-2[4-7]"
    Using the offset of the hub and the location_id of each device, we can determine the port each device is connected to
    """

    @staticmethod
    def _resolve_port_range_from_name(hub_name):
        match = re.search(r"\[([0-9])-([0-9])+\]", hub_name)
        if match is None:
            return [0, 0]
        else:
            return [int(match.group(1)), int(match.group(2))]

    @staticmethod
    def _resolve_port_number(hub_name, device_location_id):
        port_range = AcronameUSBController._resolve_port_range_from_name(hub_name)
        return (
            port_range[1]
            + 1
            - int(device_location_id.split(" ")[0].rstrip("0")[-1])
            + port_range[0]
        )

    def get_device_hub_map(self):
        return self.device_map
