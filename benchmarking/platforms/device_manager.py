#!/usr/bin/env python

##############################################################################
# Copyright 2020-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import asyncio
import datetime
import json
import os
import time

from argparse import Namespace
from collections import defaultdict
from threading import Thread

from bridge.db import DBDriver
from get_connected_devices import GetConnectedDevices
from metrics.counters import Counter
from platforms.android.adb import ADB
from platforms.battery_state import getBatteryState
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

    def __init__(self, args: Namespace, db: DBDriver):
        self.args = args
        self.db: DBDriver = db
        self.lab_devices = {}
        self.online_devices = None
        self.device_dc_count = defaultdict(int)
        self.dc_threshold = 3
        self._initializeDevices()
        self.running = True
        self.failed_device_checks = 0
        self.counter = None
        if self.args.device_counters:
            try:
                self.counter = Counter().get_counter()
            except Exception:
                getLogger().exception(
                    "Could not load device counter!  Counters will not be updated for this server!"
                )
        self.device_monitor_interval = self.args.device_monitor_interval
        self.async_event_loop = None
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

    async def _asyncRunDeviceMonitor(self):
        """Async function with device monitoring loop.  Heartbeats and counters are updated with non-blocking aiohttp calls."""
        await self._initCounters()
        while self.running:
            # if the lab is hosting mobile devices, thread will monitor connectivity of devices.
            if self.args.platform.startswith(
                "android"
            ) or self.args.platform.startswith("ios"):
                # mobile-only logic
                await self._checkDevices()
                await self._updateCounters()
            await self._updateHeartbeats()
            # await asyncio.sleep(self.device_monitor_interval)
            time.sleep(self.device_monitor_interval)
        await self._initCounters()

    def _runDeviceMonitor(self):
        self.async_event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.async_event_loop)
        self.async_event_loop.run_until_complete(self._asyncRunDeviceMonitor())
        self.async_event_loop.close()

    async def _checkDevices(self):
        """Run any device health checks, e.g. connectivity, battery, etc."""
        try:
            online_hashes = getDeviceList(self.args, silent=True)
            self._handleDCDevices(online_hashes)
            await self._handleNewDevices(online_hashes)
            self.failed_device_checks = 0
        except Exception:
            getLogger().exception("Error while checking devices.")
            self.failed_device_checks += 1
            # If 3 device checks have failed, critically log failure.
            if self.failed_device_checks == 3:
                getLogger().critical(
                    "Persistent error while checking devices.", exc_info=True
                )

    def _attempt_device_reconnect(self, hash):
        getLogger().info(f"Attempting reconnect of device with hash {hash}.")
        if not self.usb_controller:
            return False
        try:
            self.usb_controller.disconnect(hash)
            time.sleep(2)
            self.usb_controller.connect(hash)
            getLogger().info(f"USB connection for {hash} was reset.")
            time.sleep(5)
            online_hashes = getDeviceList(self.args, silent=True)
            device_online = hash in online_hashes
            if device_online:
                getLogger().info(f"Device with hash {hash} is ONLINE after reconnect.")
            else:
                getLogger().info(f"Device with hash {hash} is OFFLINE after reconnect.")
            return device_online
        except Exception:
            getLogger().exception(f"Device reconnect failed for {hash}")
            return False

    def _handleDCDevices(self, online_hashes):
        """
        If there are devices we expect to be connected to the host,
        check if they are rebooting or have been put offline by the USBController,
        else mark the device as unavailable and offline. After dc_threshold times
        that the device is not seen, remove it completely and critically log.
        """
        for h in online_hashes:
            if h in self.device_dc_count:
                device = [d for d in self.online_devices if d["hash"] == h][0]
                getLogger().info(f"Device {device} has reconnected.")
                self.device_dc_count.pop(h)
                self._enableDevice(device)
        dc_devices = [
            device
            for device in self.online_devices
            if device["hash"] not in online_hashes
        ]
        for dc_device in dc_devices:
            kind = dc_device["kind"]
            hash = dc_device["hash"]
            lab_device = self.lab_devices[kind][hash]
            usb_disabled = False
            if self.usb_controller and not self.usb_controller.active.get(hash, True):
                usb_disabled = True
            if "rebooting" not in lab_device and not usb_disabled:
                if hash not in self.device_dc_count:
                    getLogger().error(
                        f"Device {dc_device} is disconnected and has been marked unavailable for benchmarking.",
                    )
                    self._disableDevice(dc_device)
                self.device_dc_count[hash] += 1
                dc_count = self.device_dc_count[hash]
                if dc_count < self.dc_threshold:
                    getLogger().error(
                        f"Device {dc_device} has shown as disconnected {dc_count} time(s) ({dc_count * self.device_monitor_interval}s)",
                    )
                elif dc_count == self.dc_threshold:
                    reconnect = self._attempt_device_reconnect(hash)
                    if reconnect:
                        getLogger().warning(
                            f"Device {dc_device} has shown as disconnected {dc_count} time(s) and was able to be reconnected."
                        )
                    else:
                        device_offline_message = f"Device {dc_device} has shown as disconnected {dc_count} time(s) ({dc_count * self.device_monitor_interval}s) and is offline."
                        getLogger().error(device_offline_message)
                        self.online_devices.remove(dc_device)
                    self.device_dc_count.pop(hash)

    async def _handleNewDevices(self, online_hashes):
        """
        Check if there are newly detected devices connected
        to the host and add them to the device list.
        """
        new_devices = [
            h
            for h in online_hashes
            if h not in [p["hash"] for p in self.online_devices]
        ]
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
                    if d["hash"] in self.device_dc_count:
                        self.device_dc_count.pop(d["hash"])
                    getLogger().info("New device added: {}".format(d))
            await self._initCounters(devices=new_devices)

    async def _updateHeartbeats(self):
        """Update device heartbeats for all devices which are marked "live" in lab devices."""
        claimer_id = self.args.claimer_id
        hashes = []
        for k in self.lab_devices:
            for hash in self.lab_devices[k]:
                if self.lab_devices[k][hash]["live"]:
                    hashes.append(hash)
        hashes = ",".join(hashes)
        await self.db.updateHeartbeats(self.async_event_loop, claimer_id, hashes)

    async def _initCounters(self, devices=None):
        """Update counters data for devices. If devices is None, initialize all."""
        if self.args.device_counters:
            data = []
            for k in self.lab_devices:
                for hash in self.lab_devices[k]:
                    if devices is None or hash in devices:
                        data.append(
                            {
                                "key": f"aibench_devices.{os.environ.get('CLAIMER','')}.{k}.{hash}.connected",
                                "value": 0.0,
                            }
                        )
            if data:
                await self.counter.update_counters(self.async_event_loop, data)

    async def _updateCounters(self):
        """Update counters data for devices."""
        if self.args.device_counters:
            data = []
            for k in self.lab_devices:
                for hash in self.lab_devices[k]:
                    data.append(
                        {
                            "key": f"aibench_devices.{os.environ.get('CLAIMER','')}.{k}.{hash}.connected",
                            "value": 1.0 if self.lab_devices[k][hash]["live"] else 0.0,
                        }
                    )
            if data:
                await self.counter.update_counters(self.async_event_loop, data)

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

    def shutdown(self):
        self.db.updateDevices(self.args.claimer_id, "", True)
        self.running = False


class CoolDownDevice(Thread):
    """Used by AsyncRun to cool device down after benchmark.  Will reboot the device if required and add rebooting status to device entry."""

    def __init__(self, device, args, db, force_reboot, job_cooldown=None):
        Thread.__init__(self)
        self.device = device
        self.args = args
        self.db = db
        self.force_reboot = force_reboot
        if job_cooldown is not None and job_cooldown >= 0:
            self.cooldown = job_cooldown
        else:
            self.cooldown = self.args.cooldown

    def run(self):
        reboot = self.args.reboot and (
            self.force_reboot
            or self.device["reboot_time"] + REBOOT_INTERVAL < datetime.datetime.now()
        )
        success = True

        battery_state = getBatteryState(
            self.device["hash"], self.args.platform, self.args.android_dir
        )
        if battery_state["supported"]:
            getLogger().info(
                f"\nBattery status: {battery_state['status']}"
                + f"\nBattery charge level: {battery_state['charge_level']}%"
                + f"\nBattery temperature: {battery_state['temperature']}\xB0C"
            )
            if battery_state["disconnected"]:
                getLogger().warning(
                    f"Battery for {self.device} was left in a disconnected state; rebooting to restore charging."
                )
                reboot = True

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
                getLogger().critical(f"Device {self.device} could not be rebooted.")
                success = False

        not_ready = True
        charge_threshold = 30  # REVIEW
        getLogger().info(f"Sleep {self.cooldown} seconds.")
        while not_ready:
            # sleep for device cooldown
            time.sleep(self.cooldown)

            battery_state = getBatteryState(
                self.device["hash"], self.args.platform, self.args.android_dir
            )
            if (battery_state["supported"]) and battery_state[
                "charge_level"
            ] < charge_threshold:
                getLogger().info(
                    f"Battery charge of {battery_state['charge_level']}% is below threshold of {charge_threshold}%; Sleep another {self.cooldown} seconds."
                )
                continue

            not_ready = False

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
