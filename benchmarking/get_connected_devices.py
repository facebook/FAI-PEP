#!/usr/bin/env python

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

from platforms.platforms import getPlatforms
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
getParser().add_argument("--platform", default="android",
    help="Specify the platforms to benchmark on. ")
getParser().add_argument("--platform_sig",
    help="Specify the platforms signature which clusters the same type machine. ")


class GetConnectedDevices(object):
    def __init__(self):
        getLogger().setLevel(logging.FATAL)
        parse()

    def run(self):
	platforms = getPlatforms("/tmp")
        devices = []
        for p in platforms:
            devices.append({
		"kind": p.platform,
                "hash": p.platform_hash,	
	    })
        json_str = json.dumps(devices)
        print(json_str)
        return json_str


if __name__ == "__main__":
    app = GetConnectedDevices()
    app.run()
