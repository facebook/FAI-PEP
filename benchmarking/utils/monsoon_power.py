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

import json
import os
import tempfile
from time import sleep

import Monsoon.HVPM as HVPM
import Monsoon.Operations as op

import Monsoon.sampleEngine as sampleEngine
from bridge.file_storage.upload_files.file_uploader import FileUploader
from utils.custom_logger import getLogger


def collectPowerData(
    hash,
    sample_time,
    voltage,
    num_iters,
    method="monsoon",
    monsoon_map=None,
    threshold=300,
    window_size=1000,
):
    has_usb = method == "monsoon_with_usb"
    Mon = HVPM.Monsoon()
    serialno = _getMonsoonSerialno(
        device_hash=hash, monsoon_map=monsoon_map, Monsoon=Mon
    )
    if serialno is not None:
        getLogger().info(
            "Collecting current from monsoon {} for {}".format(str(serialno), hash)
        )
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
        getLogger().info("Failed to close device")
        return {}

    power_data, url = _extract_samples(samples, has_usb)

    getLogger().info(
        "Calculating the benchmark data range from "
        "{} data points".format(len(power_data))
    )
    max_range, max_low_range = _calculatePowerDataRange(
        power_data, threshold, window_size
    )
    if max_range is None or max_low_range is None:
        getLogger().error("Metric collection failed")
        return {}

    getLogger().info(
        "Collecting baseline data from "
        "{} to {}".format(max_low_range["start"], max_low_range["end"])
    )
    getLogger().info(
        "Collecting data from " "{} to {}".format(max_range["start"], max_range["end"])
    )
    getLogger().info(
        "Benchmark time: "
        "{} - {} s".format(
            power_data[max_range["start"]]["time"], power_data[max_range["end"]]["time"]
        )
    )
    data = _retrievePowerData(power_data, max_range, max_low_range, num_iters)
    data["power_trace"] = url
    return data


def _extract_samples(samples, has_usb):
    power_data = []

    prev_time_stamp = -1
    for i in range(len(samples[sampleEngine.channels.timeStamp])):
        time_stamp = samples[sampleEngine.channels.timeStamp][i]
        current = samples[sampleEngine.channels.MainCurrent][i]
        voltage = samples[sampleEngine.channels.MainVoltage][i]
        if has_usb:
            usb_current = samples[sampleEngine.channels.USBCurrent][i]
            usb_voltage = samples[sampleEngine.channels.USBVoltage][i]
        # there is a bug that two consecutive time stamps may be identical
        # patch it by evenly divide the timestamps
        if i >= 2 and prev_time_stamp == time_stamp:
            power_data[-1]["time"] = (power_data[-2]["time"] + time_stamp) / 2
        prev_time_stamp = time_stamp
        data = {
            "time": time_stamp,
            "current": current,
            "voltage": voltage,
            "usb_current": 0,
            "usb_voltage": 0,
        }
        if has_usb:
            data["usb_current"] = usb_current
            data["usb_voltage"] = usb_voltage

        power_data.append(data)

    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, prefix="power_data_", suffix=".csv"
    ) as f:
        filename = f.name
        getLogger().info("Writing power data to file: {}".format(f.name))
        f.write("time, current, voltage, usb_current, usb_voltage\n")
        for i in range(len(power_data)):
            entry = power_data[i]
            f.write(
                f"{entry['time']}, {entry['current']}, {entry['voltage']}, {entry['usb_current']}, {entry['usb_voltage']}\n"
            )

    getLogger().info(f"Uploading power file {filename}")
    output_file_uploader = FileUploader("output_files").get_uploader()
    url = output_file_uploader.upload_file(filename)
    getLogger().info(f"Uploaded power url {url}")
    os.unlink(filename)
    return power_data, url


def _get_sum_current(power_data, start, end, window_size):
    # Get the total current in the window
    sum = 0
    for i in range(start, min(start + window_size, end)):
        sum += power_data[i]["current"]
        sum += power_data[i]["usb_current"]
    return i, sum


def _find_first_window_below_threshold(
    power_data, initial_sum, start, end, window_size, threshold
):
    return _find_first_window(
        power_data, initial_sum, start, end, window_size, threshold, False
    )


def _find_first_window_above_threshold(
    power_data, initial_sum, start, end, window_size, threshold
):
    return _find_first_window(
        power_data, initial_sum, start, end, window_size, threshold, True
    )


def _find_first_window(
    power_data, initial_sum, start, end, window_size, threshold, above=True
):
    assert start >= window_size - 1
    i = start
    sum = initial_sum
    while i < end - 1 and (
        (sum / window_size) < threshold if above else (sum / window_size) > threshold
    ):
        # moving average advance one step
        i = i + 1
        sum = (
            sum
            - power_data[i - window_size]["current"]
            - power_data[i - window_size]["usb_current"]
            + power_data[i]["current"]
            + power_data[i]["usb_current"]
        )
    return i, sum


def _calculateOnePowerDataRange(
    power_data, num, i, sum, threshold=300, window_size=1000
):
    # first find the average current is less than the threshold
    i, sum = _find_first_window_below_threshold(
        power_data, sum, i, num, window_size, threshold
    )

    # find the first window whose average current is above the threshold
    i, sum = _find_first_window_above_threshold(
        power_data, sum, i, num, window_size, threshold
    )

    window_i = i

    # find the last entry below threshold
    while (
        i > 0 and (power_data[i]["current"] + power_data[i]["usb_current"]) > threshold
    ):
        i = i - 1
    # find the min of the constant decreasing current
    while i > 0 and (
        power_data[i - 1]["current"] + power_data[i - 1]["usb_current"]
    ) < (power_data[i]["current"] + power_data[i]["usb_current"]):
        i = i - 1

    # have found a possible start of the benchmark
    start = i

    # find the first window whose current is below threshold again
    i, sum = _find_first_window_below_threshold(
        power_data, sum, window_i, num, window_size, threshold
    )
    ii = max(0, i - window_size)

    # get the first entry below threshold
    while (
        ii < num
        and (power_data[ii]["current"] + power_data[ii]["usb_current"]) > threshold
    ):
        ii = ii + 1
    # get the min of the constant decreasing current
    while ii < num - 1 and (
        power_data[ii]["current"] + power_data[ii]["usb_current"]
    ) > (power_data[ii + 1]["current"] + power_data[ii + 1]["usb_current"]):
        ii = ii + 1

    # found a possible end of the benchmark
    end = ii - 1

    return start, end, i, sum


# This only works in one specific scenario:
# In the beginning, the current is low and below threshold
# Then there is a sudden jump in current and the current keeps high
# After the benchmark, the current restores back to below threshold for some time
# All other scenarios are not caught
def _calculatePowerDataRange(power_data, threshold=300, window_size=1000):
    num = len(power_data)
    if num <= window_size:
        getLogger().error(
            f"Collected {num} samples from monsoon, which is less than the window size of {window_size}"
        )
        return None, None
    # first get the sum of the window size values
    i, sum = _get_sum_current(power_data, 0, num, window_size)

    ranges = []
    while i < num - 1:
        start, end, i, sum = _calculateOnePowerDataRange(
            power_data, num, i, sum, threshold, window_size
        )
        if (start < num) and (end <= num) and (start < end):
            ranges.append({"start": start, "end": end})

    if len(ranges) == 0:
        getLogger().error(
            "Cannot collect any useful metric from the monsoon data. Please examine the benchmark setting."
        )
        return None, None

    # get the max range of all collected ranges
    max_range = ranges[0]
    r_start = 0
    for r in ranges:
        assert r["end"] >= r["start"]
        assert r["start"] >= r_start
        r_start = r["end"]
        if r["end"] - r["start"] > max_range["end"] - max_range["start"]:
            max_range = r

    # get the range below the threshold
    low_ranges = [{"start": 0, "end": -1}]
    for r in ranges:
        low_ranges[-1]["end"] = max(r["start"] - 1, low_ranges[-1]["start"])
        low_ranges.append({"start": r["end"] + 1, "end": -1})
    low_ranges[-1]["end"] = num - 1

    # get the max range that is below the threshold
    max_low_range = low_ranges[0]
    for r in low_ranges:
        if r["end"] - r["start"] > max_low_range["end"] - max_low_range["start"]:
            max_low_range = r
    getLogger().info(ranges)
    getLogger().info(low_ranges)
    # the test needs to be designed in a way that more than half of the collected
    # data is executing the model.
    """
    assert (
        max_range["end"] - max_range["start"] >= num / 2
    ), f"Test needs to be designed that over half of the collected data is model execution. "
    """
    return max_range, max_low_range


def _retrievePowerData(power_data, high_range, low_range, num_iters):
    data = {}
    if high_range["start"] < 0 or high_range["end"] < 0:
        return data

    # get base current. It is just an approximation

    total_current = 0
    total_usb_current = 0
    count = 0
    for i in range(low_range["start"], low_range["end"]):
        total_current += power_data[i]["current"]
        total_usb_current += power_data[i]["usb_current"]
        count += 1
    base_current = total_current / count if count > 0 else 0
    base_usb_current = total_usb_current / count if count > 0 else 0

    energy = 0
    prev_time = power_data[max(0, high_range["start"] - 1)]["time"]
    for i in range(high_range["start"], high_range["end"]):
        entry = power_data[i]
        curr_time = entry["time"]
        energy += (
            entry["voltage"] * (entry["current"] - base_current)
            + entry["usb_voltage"] * (entry["usb_current"] - base_usb_current)
        ) * (curr_time - prev_time)
        prev_time = curr_time
    total_time = (
        power_data[high_range["end"]]["time"] - power_data[high_range["start"]]["time"]
    )
    power = energy / total_time
    energy_per_inference = energy / num_iters
    latency = total_time * 1000 * 1000 / num_iters
    data["energy"] = _composeStructuredData(energy_per_inference, "energy", "mJ")
    data["power"] = _composeStructuredData(power, "power", "mW")
    data["latency"] = _composeStructuredData(latency, "latency", "uS")

    getLogger().info(f"Number of iterations: {num_iters}")
    getLogger().info("Base current: {} mA".format(base_current))
    getLogger().info("Energy per inference: {} mJ".format(energy_per_inference))
    getLogger().info("Power: {} mW".format(power))
    getLogger().info("Latency per inference: {} uS".format(latency))
    return data


def _composeStructuredData(data, metric, unit):
    return {
        "values": [data],
        "type": "NET",
        "metric": metric,
        "unit": unit,
        "summary": {
            "p0": data,
            "p10": data,
            "p50": data,
            "p90": data,
            "p100": data,
            "mean": data,
            "stdev": 0,
            "MAD": 0,
        },
    }


def _getMonsoonSerialno(device_hash, monsoon_map=None, Monsoon=None):
    if monsoon_map:
        mapping = json.loads(monsoon_map)
        serialno = mapping.get(device_hash, None)
    if not serialno and len(Monsoon.enumerateDevices()) > 1:
        getLogger().info(
            f"Device {device_hash} is not associated with a specific power monitor, but there are {len(Monsoon.enumerateDevices())} Monsoon monitors connected ({Monsoon.enumerateDevices()}). Please add --monsoon_map to specify the mapping between device hash and Monsoon serial number"
        )
    return serialno
