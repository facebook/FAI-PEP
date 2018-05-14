#!/usr/bin/env python3

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json
import logging

from platforms.android.android_driver import AndroidDriver
from utils.arg_parse import getParser, parse
from utils.custom_logger import getLogger


getParser().add_argument("-d", "--devices",
    help="Specify the devices to run the benchmark, in a comma separated "
    "list. The value is the device or device_hash field of the meta info.")
getParser().add_argument("--device",
    help="The single device to run this benchmark on")
getParser().add_argument("--excluded_devices",
    help="Specify the devices that skip the benchmark, in a comma separated "
    "list. The value is the device or device_hash field of the meta info.")
getParser().add_argument("--set_freq",
    help="On rooted android phones, set the frequency of the cores. "
    "The supported values are: "
    "max: set all cores to the maximum frquency. "
    "min: set all cores to the minimum frequency. "
    "mid: set all cores to the median frequency. ")


class GetConnectedAndroids(object):
    def __init__(self):
        getLogger().setLevel(logging.FATAL)
        parse()

    def run(self):
        driver = AndroidDriver()
        platforms = driver.getAndroidPlatforms("")
        androids = []
        for p in platforms:
            androids.append({
                "kind": p.platform,
                "hash": p.platform_hash,
            })
        json_str = json.dumps(androids)
        print(json_str)
        return json_str


if __name__ == "__main__":
    app = GetConnectedAndroids()
    app.run()
