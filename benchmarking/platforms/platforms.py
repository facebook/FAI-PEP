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

import os

from utils.custom_logger import getLogger

from .android.android_driver import AndroidDriver
from .host.host_platform import HostPlatform
from .ios.ios_driver import IOSDriver
from .windows.windows_platform import WindowsPlatform


def getPlatforms(args, tempdir="/tmp", usb_controller=None):
    platforms = []
    if (
        args.platform[:4] == "host"
        or args.platform[:5] == "linux"
        or args.platform[:3] == "mac"
    ):
        platforms.append(HostPlatform(tempdir, args))
    elif args.platform[:7] == "android":
        driver = AndroidDriver(args)
        platforms.extend(driver.getAndroidPlatforms(tempdir, usb_controller))
    elif args.platform.startswith("ios"):
        driver = IOSDriver(args)
        platforms.extend(driver.getIOSPlatforms(tempdir, usb_controller))
    elif os.name == "nt":
        platforms.append(WindowsPlatform(tempdir))
    if not platforms:
        getLogger().error("No platform or physical device detected.")
    return platforms


def getDeviceList(args, silent=False, retry=1):
    assert args.platform in (
        "android",
        "ios",
    ), "This is only supported for mobile platforms."
    deviceList = []
    if args.platform.startswith("android"):
        driver = AndroidDriver(args)
        deviceList.extend(driver.getDevices(silent, retry))
    elif args.platform.startswith("ios"):
        driver = IOSDriver(args)
        deviceList.extend(driver.getDevices(silent, retry))
    return deviceList


def getHostPlatform(tempdir, args):
    if os.name == "nt":
        return WindowsPlatform(tempdir)
    else:
        return HostPlatform(tempdir, args)
