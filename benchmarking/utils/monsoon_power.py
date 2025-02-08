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
import os
import tempfile
from time import sleep

import Monsoon.HVPM as HVPM
import Monsoon.Operations as op

import Monsoon.sampleEngine as sampleEngine
from bridge.file_storage.upload_files.file_uploader import FileUploader
from utils.custom_logger import getLogger
from utils.power_utils import post_process_power_data


def collectPowerData(
    hash,
    sample_time,
    voltage,
    num_iters,
    method="monsoon",
    monsoon_map=None,
):
    has_usb = method == "monsoon_with_usb"
    Mon = HVPM.Monsoon()
    serialno = _getMonsoonSerialno(
        device_hash=hash, monsoon_map=monsoon_map, Monsoon=Mon
    )
    if serialno is not None:
        getLogger().info(f"Collecting current from monsoon {str(serialno)} for {hash}")
    # wait till all actions are performed
    sleep(1)
    Mon.setup_usb(serialno)
    # Need to sleep to be functional correctly
    # there may have some race condition, so need to sleep sufficiently long.
    sleep(0.5)
    getLogger().info(f"Setup Vout: {voltage}")
    Mon.setVout(voltage)
    getLogger().info("Setup setPowerupTime: 60")
    Mon.setPowerupTime(60)
    getLogger().info("Setup setPowerUpCurrentLimit: 14")
    Mon.setPowerUpCurrentLimit(14)
    getLogger().info("Setup setRunTimeCurrentLimit: 14")
    Mon.setRunTimeCurrentLimit(14)
    Mon.fillStatusPacket()

    # main channel
    getLogger().info("Setup setVoltageChannel: 0")
    Mon.setVoltageChannel(0)

    engine = sampleEngine.SampleEngine(Mon)
    engine.disableCSVOutput()
    getLogger().info("Disable ConsoleOutput")
    engine.ConsoleOutput(False)
    getLogger().info("Enable main current")
    engine.enableChannel(sampleEngine.channels.MainCurrent)
    getLogger().info("Enable main voltage")
    engine.enableChannel(sampleEngine.channels.MainVoltage)
    if has_usb:
        getLogger().info("Enable usb current")
        engine.enableChannel(sampleEngine.channels.USBCurrent)
        getLogger().info("Enable usb voltage")
        engine.enableChannel(sampleEngine.channels.USBVoltage)
        Mon.setUSBPassthroughMode(op.USB_Passthrough.On)
    else:
        getLogger().info("Disable usb current")
        engine.disableChannel(sampleEngine.channels.USBCurrent)
        getLogger().info("Disable usb voltage")
        engine.disableChannel(sampleEngine.channels.USBVoltage)
        Mon.setUSBPassthroughMode(op.USB_Passthrough.Auto)

    sleep(1)
    # 200 us per sample
    num_samples = sample_time / 0.0002
    getLogger().info("startSampling")
    engine.startSampling(num_samples)

    samples = engine.getSamples()

    # device may not be available,
    # try reconnect 5 times before fail
    repeat = 0
    while repeat < 5:
        try:
            getLogger().info("Closing device")
            Mon.closeDevice()
            break
        except Exception:
            repeat = repeat + 1
            sleep(2)
    if repeat >= 5:
        raise Exception("Failed to close device")

    power_data, url = _extract_samples(samples, has_usb)

    data = post_process_power_data(power_data, sample_rate=5000, num_iters=num_iters)
    data["power_trace"] = url

    return data


def _extract_samples(samples, has_usb):
    power_data = {
        "time": [],
        "current": [],
        "voltage": [],
        "usb_current": [],
        "usb_voltage": [],
        "total_power": [],
    }

    for i in range(len(samples[sampleEngine.channels.timeStamp])):
        time_stamp = samples[sampleEngine.channels.timeStamp][i]
        current = samples[sampleEngine.channels.MainCurrent][i]
        voltage = samples[sampleEngine.channels.MainVoltage][i]
        if has_usb:
            usb_current = samples[sampleEngine.channels.USBCurrent][i]
            usb_voltage = samples[sampleEngine.channels.USBVoltage][i]
        power_data["time"].append(time_stamp)
        power_data["current"].append(current)
        power_data["voltage"].append(voltage)
        if has_usb:
            power_data["usb_current"].append(usb_current)
            power_data["usb_voltage"].append(usb_voltage)
            power_data["total_power"].append(
                (current * voltage) + (usb_current * usb_voltage)
            )
        else:
            power_data["usb_current"].append(0)
            power_data["usb_voltage"].append(0)
            power_data["total_power"].append(current * voltage)

    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, prefix="power_data_", suffix=".csv"
    ) as f:
        filename = f.name
        getLogger().info(f"Writing power data to file: {f.name}")
        f.write("time, current, voltage, usb_current, usb_voltage, total_power\n")
        for i in range(len(power_data["time"])):
            f.write(
                f"{power_data['time'][i]:.4f}, {power_data['current'][i]:.4f}, "
                f"{power_data['voltage'][i]:.4f}, {power_data['usb_current'][i]:.4f}, "
                f"{power_data['usb_voltage'][i]:.4f}, {power_data['total_power'][i]:.4f}\n"
            )

    getLogger().info(f"Uploading power file {filename}")
    output_file_uploader = FileUploader("output_files").get_uploader()
    url = output_file_uploader.upload_file(filename)
    getLogger().info(f"Uploaded power url {url}")
    os.unlink(filename)
    return power_data, url


def _getMonsoonSerialno(device_hash, monsoon_map=None, Monsoon=None):
    if monsoon_map:
        mapping = json.loads(monsoon_map)
        serialno = mapping.get(device_hash, None)
    if not serialno and len(Monsoon.enumerateDevices()) > 1:
        getLogger().info(
            f"Device {device_hash} is not associated with a specific power monitor, "
            f"but there are {len(Monsoon.enumerateDevices())} Monsoon monitors "
            f"connected: {Monsoon.enumerateDevices()}. Please add --monsoon_map to "
            f"specify the mapping between device hash and Monsoon serial number"
        )

    return serialno
