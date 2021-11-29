#!/usr/bin/env python

##############################################################################
# Copyright 2020-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime
import json
import time
from threading import Thread
from typing import Dict

from bridge.db import DBDriver
from get_connected_devices import GetConnectedDevices
from platforms.android.adb import ADB
from platforms.platforms import getDeviceList
from reboot_device import reboot as reboot_device
from utils.custom_logger import getLogger

REBOOT_INTERVAL = datetime.timedelta(hours=8)
MINIMUM_DM_INTERVAL = 10
DEFAULT_DM_INTERVAL = 10


def getDevicesString(devices):
    device_list = [
        d["kind"]
        + "|"
        + d["hash"]
        + "|"
        + d["name"]
        + "|"
        + d["abi"]
        + "|"
        + d["os"]
        + "|"
        + ("1" if d["available"] else "0" if d["live"] else "2")
        for d in devices
    ]
    devices_str = ",".join(device_list)
    return devices_str


def valid_dm_interval(arg) -> int:
    try:
        value = int(arg)
        if value < MINIMUM_DM_INTERVAL:
            raise ValueError()
    except ValueError:
        getLogger().warning(
            "Logging interval must be specified as an integer in seconds >= {}.  Using default {}s.".format(
                MINIMUM_DM_INTERVAL, DEFAULT_DM_INTERVAL
            )
        )
        value = DEFAULT_DM_INTERVAL
    return value


class DeviceManager(object):
    """
    Provides devices metadata to the lab instance. For mobile platforms, checks connectivity of devices and performs updates to lab devices and db.
    """

    def __init__(self, args: Dict, db: DBDriver):
        self.args = args
        self.db: DBDriver = db
        self.lab_devices = {}
        self.online_devices = None
        self._initializeDevices()
        self.running = True
        self.device_monitor_interval = self.args.device_monitor_interval
        self.device_monitor = Thread(target=self._runDeviceMonitor)
        self.device_monitor.start()
        if self.args.usb_hub_device_mapping:
            from utils.usb_controller import USBController

            self.usb_controller = USBController(self.args.usb_hub_device_mapping)
        else:
            self.usb_controller = None

    def getLabDevices(self):
        """Return a reference to the lab's device meta data."""
        return self.lab_devices

    def _runDeviceMonitor(self):
        while self.running:
            # if the lab is hosting mobile devices, thread will monitor connectivity of devices.
            if self.args.platform.startswith(
                "android"
            ) or self.args.platform.startswith("ios"):
                self._checkDevices()
            self._updateHeartbeats()
            time.sleep(self.device_monitor_interval)

    def _checkDevices(self):
        """Run any device health checks, e.g. connectivity, battery, etc."""
        try:
            online_hashes = getDeviceList(self.args, silent=True)
            offline_devices = [
                device
                for device in self.online_devices
                if device["hash"] not in online_hashes
            ]
            new_devices = [
                h
                for h in online_hashes
                if h not in [p["hash"] for p in self.online_devices]
            ]
            if offline_devices:
                for offline_device in offline_devices:
                    lab_device = self.lab_devices[offline_device["kind"]][
                        offline_device["hash"]
                    ]
                    usb_disabled = False
                    if self.usb_controller and not self.usb_controller.active.get(
                        lab_device["hash"], True
                    ):
                        usb_disabled = True
                    if "rebooting" not in lab_device and not usb_disabled:
                        getLogger().error(
                            "Device {} has become unavailable.".format(offline_device)
                        )
                        self._disableDevice(offline_device)
            if new_devices:
                devices = ",".join(new_devices)
                devices = self._getDevices(devices)
                if devices:
                    for d in devices:
                        self._enableDevice(d)
                        if d["hash"] not in [
                            device["hash"] for device in self.online_devices
                        ]:
                            self.online_devices.append(d)
                        getLogger().info("New device added: {}".format(d))
        except BaseException:
            getLogger().exception("Error while checking devices.")

    def _updateHeartbeats(self):
        """Update device heartbeats for all devices which are marked "live" in lab devices."""
        claimer_id = self.args.claimer_id
        hashes = []
        for k in self.lab_devices:
            for hash in self.lab_devices[k]:
                if self.lab_devices[k][hash]["live"]:
                    hashes.append(hash)
        hashes = ",".join(hashes)
        self.db.updateHeartbeats(claimer_id, hashes)

    def _getDevices(self, devices=None):
        """Get list of device meta data for available devices."""
        raw_args = []
        raw_args.extend(["--platform", self.args.platform])
        if self.args.platform_sig:
            raw_args.append("--platform_sig")
            raw_args.append(self.args.platform_sig)
        if devices:
            raw_args.append("--devices")
            raw_args.append(devices)
        elif self.args.devices:
            raw_args.append("--devices")
            raw_args.append(self.args.devices)
        if self.args.hash_platform_mapping:
            # if the user provides filename, we will load it.
            raw_args.append("--hash_platform_mapping")
            raw_args.append(self.args.hash_platform_mapping)
        if self.args.device_name_mapping:
            # if the user provides filename, we will load it.
            raw_args.append("--device_name_mapping")
            raw_args.append(self.args.device_name_mapping)
        app = GetConnectedDevices(raw_args=raw_args)
        devices_json = app.run()
        assert devices_json, "Devices cannot be empty"
        devices = json.loads(devices_json.strip())
        return devices

    def _initializeDevices(self):
        """Create device meta data used by lab instance, and update devices in db."""
        self.online_devices = self._getDevices()
        for k in self.online_devices:
            kind = k["kind"]
            hash = k["hash"]
            name = k["name"]
            abi = k["abi"]
            os = k["os"]
            entry = {
                "kind": kind,
                "hash": hash,
                "name": name,
                "abi": abi,
                "os": os,
                "available": True,
                "live": True,
                "start_time": None,
                "done_time": None,
                "output_dir": None,
                "job": None,
                "adb": ADB(hash, self.args.android_dir),
                "reboot_time": datetime.datetime.now() - datetime.timedelta(hours=8),
                "usb_hub": {},
            }
            if kind not in self.lab_devices:
                self.lab_devices[kind] = {}
            self.lab_devices[kind][hash] = entry
        dvs = [
            self.lab_devices[k][h]
            for k in self.lab_devices
            for h in self.lab_devices[k]
        ]
        self.db.updateDevices(self.args.claimer_id, getDevicesString(dvs), True)

    def _disableDevice(self, device):
        kind = device["kind"]
        hash = device["hash"]
        entry = self.lab_devices[kind][hash]
        entry["available"] = False
        entry["live"] = False
        self.online_devices.remove(device)
        self.db.updateDevices(
            self.args.claimer_id,
            getDevicesString([self.lab_devices[kind][hash]]),
            False,
        )

    def _enableDevice(self, device):
        kind = device["kind"]
        hash = device["hash"]
        name = device["name"]
        abi = device["abi"]
        os = device["os"]
        entry = {
            "kind": kind,
            "hash": hash,
            "name": name,
            "abi": abi,
            "os": os,
            "available": True,
            "live": True,
            "start_time": None,
            "done_time": None,
            "output_dir": None,
            "job": None,
            "adb": ADB(hash, self.args.android_dir),
            "reboot_time": datetime.datetime.now() - datetime.timedelta(hours=8),
            "usb_hub": {},
        }
        if kind not in self.lab_devices:
            self.lab_devices[kind] = {}
        self.lab_devices[kind][hash] = entry
        self.db.updateDevices(
            self.args.claimer_id,
            getDevicesString([self.lab_devices[kind][hash]]),
            False,
        )

    def _sendErrorReport(self, emsg):
        # TODO: send alert to support team to troubleshoot
        raise NotImplementedError

    def shutdown(self):
        self.db.updateDevices(self.args.claimer_id, "", True)
        self.running = False


class CoolDownDevice(Thread):
    """Used by AsyncRun to cool device down after benchmark.  Will reboot the device if required and add rebooting status to device entry."""

    def __init__(self, device, args, db, force_reboot):
        Thread.__init__(self)
        self.device = device
        self.args = args
        self.db = db
        self.force_reboot = force_reboot

    def run(self):
        reboot = self.args.reboot and (
            self.force_reboot
            or self.device["reboot_time"] + REBOOT_INTERVAL < datetime.datetime.now()
        )
        success = True
        # reboot mobile devices if required
        if reboot:
            raw_args = []
            raw_args.extend(["--platform", self.args.platform])
            raw_args.extend(["--device", self.device["hash"]])
            raw_args.extend(["--android_dir", self.args.android_dir])
            self.device["rebooting"] = True
            if reboot_device(raw_args=raw_args):
                getLogger().info("Device {} was rebooted.".format(self.device))
                self.device["reboot_time"] = datetime.datetime.now()
            else:
                self.device.pop("rebooting")
                getLogger().error(
                    "Device {} could not be rebooted.".format(self.device)
                )
                success = False

        # sleep for device cooldown
        if self.args.platform.startswith("ios") or self.args.platform.startswith(
            "android"
        ):
            getLogger().info("Sleep 180 seconds")
            time.sleep(180)
        else:
            getLogger().info("Sleep 20 seconds")
            time.sleep(20)

        # device should be available again, remove rebooting flag.
        if "rebooting" in self.device:
            del self.device["rebooting"]
        if success:
            self.device["available"] = True
            device_str = getDevicesString([self.device])
            self.db.updateDevices(self.args.claimer_id, device_str, False)
            getLogger().info(
                "Device {}({}) available".format(
                    self.device["kind"], self.device["hash"]
                )
            )
        else:
            self.device["live"] = False
        getLogger().info("CoolDownDevice lock released")
