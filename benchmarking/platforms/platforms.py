#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import os

from .android.android_driver import AndroidDriver
from .host.host_platform import HostPlatform
from .ios.ios_driver import IOSDriver
from .windows.windows_platform import WindowsPlatform
from utils.arg_parse import getArgs
from utils.custom_logger import getLogger


def getPlatforms(tempdir):
    platforms = []
    if getArgs().platform[:4] == "host" or \
       getArgs().platform[:5] == "linux" or \
       getArgs().platform[:3] == "mac":
        platforms.append(HostPlatform(tempdir))
    elif getArgs().platform[:7] == "android":
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
    elif getArgs().platform.startswith("ios"):
        driver = IOSDriver()
        platforms.extend(driver.getIOSPlatforms(tempdir))
    elif os.name == "nt":
        platforms.append(WindowsPlatform(tempdir))
    if not platforms:
        getLogger().error("No platform or physical device detected.")
    return platforms
