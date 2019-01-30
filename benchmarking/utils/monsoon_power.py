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
import tempfile
from time import sleep

import Monsoon.HVPM as HVPM
import Monsoon.sampleEngine as sampleEngine
from utils.custom_logger import getLogger


def collectPowerData(hash, sample_time, voltage, num_iters, monsoon_map=None):
    serialno = _getSerialno(hash, monsoon_map)
    if serialno is not None:
        getLogger().info("Collecting current from "
                         "monsoon {} for {}".format(str(serialno), hash))
    # wait till all actions are performed
    sleep(1)
    Mon = HVPM.Monsoon()
    Mon.setup_usb(serialno)
    # Need to sleep to be functional correctly
    sleep(0.2)
    getLogger().info("Setup Vout")
    Mon.setVout(voltage)
    getLogger().info("Setup setPowerupTime")
    Mon.setPowerupTime(60)
    getLogger().info("Setup setPowerUpCurrentLimit")
    Mon.setPowerUpCurrentLimit(14)
    getLogger().info("Setup setRunTimeCurrentLimit")
    Mon.setRunTimeCurrentLimit(14)

    # main channel
    getLogger().info("Setup setVoltageChannel")
    Mon.setVoltageChannel(0)

    engine = sampleEngine.SampleEngine(Mon)
    getLogger().info("Setup enableCSVOutput")
    # we may leak the file content
    f = tempfile.NamedTemporaryFile(delete=False)
    f.close()
    filename = f.name
    engine.enableCSVOutput(filename)
    getLogger().info("Setup ConsoleOutput")
    engine.ConsoleOutput(False)

    sleep(1)
    # 200 us per sample
    num_samples = sample_time / 0.0002
    getLogger().info("startSampling on {}".format(filename))
    engine.startSampling(num_samples)

    engine.disableCSVOutput()
    getLogger().info("Written power data to file: {}".format(filename))

    # retrieve statistics from the power data
    getLogger().info("Reading data from CSV file")
    power_data = _getPowerData(filename)
    getLogger().info("Calculating the benchmark data range from "
                     "{} data points".format(len(power_data)))
    start_idx, end_idx = _calculatePowerDataRange(power_data)
    getLogger().info("Collecting data from "
                     "{} to {}".format(start_idx, end_idx))
    getLogger().info("Benchmark time: "
                     "{} - {} s".format(power_data[start_idx]["time"],
                                        power_data[end_idx]["time"]))
    data = _retrievePowerData(power_data, start_idx, end_idx, num_iters)
    data["power_data"] = filename
    return data


def _getPowerData(filename):
    lines = []
    with open(filename, 'r') as f:
        # skip the first line since it is the title
        line = f.readline()
        while line != "":
            line = f.readline()
            # only the main output channel is enabled
            pattern = re.compile(r"^([\d|\.]+),([\d|\.]+),([\d|\.]+),")
            match = pattern.match(line)
            if match:
                new_line = {
                    "time": float(match.group(1)),
                    "current": float(match.group(2)),
                    "voltage": float(match.group(3))
                }
                lines.append(new_line)
    return lines


# This only works in one specific scenario:
# In the beginning, the current is low and below threshold
# Then there is a sudden jump in current and the current keeps high
# After the test, the current restores back to below threshold for some time
# All other scenarios are not caught
def _calculatePowerDataRange(power_data):
    num = len(power_data)
    WINDOW_SIZE = 500
    THRESHOLD = 150
    if num <= WINDOW_SIZE:
        return -1, -1
    # first get the sum of the window size values
    sum = 0
    for i in range(WINDOW_SIZE):
        sum += power_data[i]["current"]

    ranges = []
    i = WINDOW_SIZE - 1
    while i < num - 1:
        # first find the average current is less than the threshold
        while i < num - 1 and (sum / WINDOW_SIZE) > THRESHOLD:
            i = i + 1
            sum = sum - power_data[i - WINDOW_SIZE]["current"] + \
                power_data[i]["current"]
        # find the first item with sudden jump in current
        while i < num - 1 and ((sum / WINDOW_SIZE) <= THRESHOLD) and \
                ((power_data[i]["current"] < THRESHOLD) or
                 (power_data[i]["current"] < 2 * (sum / WINDOW_SIZE))):
            i = i + 1
            sum = sum - power_data[i - WINDOW_SIZE]["current"] + \
                power_data[i]["current"]
        # find the last entry below threshold
        while i > 0 and power_data[i]["current"] > THRESHOLD:
            i = i - 1
        start = i
        # find the last item whose current is above THRESHOLD but
        # all later items are below THRESHOLD
        sum = 0
        while i < num - 1 and i < start + WINDOW_SIZE:
            i = i + 1
            sum += power_data[i]["current"]
        # wait till the average of the current is below threshold
        while i < num - 1 and ((sum / WINDOW_SIZE) > THRESHOLD):
            i = i + 1
            sum = sum - power_data[i - WINDOW_SIZE]["current"] + \
                power_data[i]["current"]
        # get the last entry below threshold
        end = i
        while end > i - WINDOW_SIZE and \
                (power_data[end-1]["current"] < THRESHOLD):
            end = end - 1
        if start < num and end < num:
            ranges.append({
                "start": start,
                "end": end
            })

    if len(ranges) == 0:
        return -1, -1
    # get the max range of all collected ranges
    max_range = ranges[0]
    for r in ranges:
        if r["end"] - r["start"] > \
                max_range["end"] - max_range["start"]:
            max_range = r
    return max_range["start"], max_range["end"]


def _retrievePowerData(power_data, start_idx, end_idx, num_iters):
    data = {}
    if start_idx < 0 or end_idx < 0:
        return data

    # get base current. It is just an approximation
    THRESHOLD = 150
    num = len(power_data)
    i = end_idx
    sum = 0
    count = 0
    for i in range(end_idx, num):
        if power_data[i]["current"] < THRESHOLD:
            sum += power_data[i]["current"]
            count += 1
    base_current = sum / count if count > 0 else 0

    energy = 0
    prev_time = power_data[start_idx - 1]["time"]
    for i in range(start_idx, end_idx):
        entry = power_data[i]
        curr_time = entry["time"]
        energy += entry["voltage"] * \
            (entry["current"] - base_current) * (curr_time - prev_time)
        prev_time = curr_time
    total_time = power_data[end_idx]["time"] - power_data[start_idx]["time"]
    power = energy / total_time
    energy_per_inference = energy / num_iters
    latency = total_time * 1000 * 1000 / num_iters
    data["energy"] = _composeStructuredData(energy_per_inference,
                                            "energy", "mJ")
    data["power"] = _composeStructuredData(power, "power", "mW")
    data["latency"] = _composeStructuredData(latency, "latency", "uS")
    getLogger().info("Base current: {} mA".format(base_current))
    getLogger().info("Energy per inference: {} mJ".format(
        energy_per_inference))
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
        }
    }


def _getSerialno(hash, monsoon_map=None):
    serialno = None
    if monsoon_map:
        map = json.loads(monsoon_map)
        if hash in map:
            serialno = map[hash]
    return serialno
