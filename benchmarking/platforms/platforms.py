#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from platforms.android.android_driver import AndroidDriver
from platforms.host.host_platform import HostPlatform
from utils.arg_parse import getArgs
from utils.custom_logger import getLogger


def getPlatforms(tempdir):
    platforms = []
    if getArgs().platform[0:4] == "host" or \
       getArgs().platform[0:5] == "linux" or \
       getArgs().platform[0:3] == "mac":
        platforms.append(HostPlatform(tempdir))
    elif getArgs().platform[0:7] == "android":
        driver = AndroidDriver()
        platforms.extend(driver.getAndroidPlatforms(tempdir))
        if getArgs().excluded_devices:
            excluded_devices = getArgs().excluded_devices.strip().split(',')
            platforms = \
                [p for p in platforms if p.platform not in excluded_devices and
                 (p.platform_hash is None or
                  p.platform_hash not in excluded_devices)]
        if getArgs().devices:
            plts = getArgs().devices.strip().split(',')
            platforms = [p for p in platforms if p.platform in plts or
                         p.platform_hash in plts]
    if not platforms:
        getLogger().error("No platform is specified.")
    return platforms
