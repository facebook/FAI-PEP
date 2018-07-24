#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import Monsoon.HVPM as HVPM
import Monsoon.sampleEngine as sampleEngine
from utils.custom_logger import getLogger

import tempfile
from time import sleep


def collectPowerData(sample_time):
    # wait till all actions are performed
    sleep(1)
    Mon = HVPM.Monsoon()
    Mon.setup_usb()
    # Need to sleep to be functional correctly
    sleep(0.2)
    getLogger().info("Setup Vout")
    Mon.setVout(4.5)
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
    getLogger().info("startSampling")
    engine.startSampling(num_samples)

    engine.disableCSVOutput()
    getLogger().info("Written power data to file: {}".format(filename))
    # wait till the device is reclaimed
    sleep(5)
    data = {
        "power": filename
    }
    return data
