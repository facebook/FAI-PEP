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

import os

from utils.custom_logger import getLogger

from .android.android_driver import AndroidDriver  # noqa
from .driver_base import getDriverHandles
from .host.host_platform import HostPlatform
from .ios.ios_driver import IOSDriver  # noqa
from .windows.windows_platform import WindowsPlatform


def getPlatforms(args, tempdir="/tmp", usb_controller=None):
    driverHandles = getDriverHandles()
    platforms = []

    for driverClass in driverHandles.values():
        if driverClass.matchPlatformArgs(args):
            driver = driverClass(args)
            platforms.extend(driver.getPlatforms(tempdir, usb_controller))

    if (
        args.platform[:4] == "host"
        or args.platform[:5] == "linux"
        or args.platform[:3] == "mac"
    ):
        platforms.append(HostPlatform(tempdir, args))
    elif os.name == "nt":
        platforms.append(WindowsPlatform(tempdir))

    if not platforms:
        getLogger().warning("No platform or physical device detected.")
    return platforms


def getDeviceList(args, silent=False, retry=1):
    assert args.platform in (
        "android",
        "ios",
    ), "This is only supported for mobile platforms."
    deviceList = []
    driverHandles = getDriverHandles()
    for driverClass in driverHandles.values():
        if driverClass.matchPlatformArgs(args):
            driver = driverClass(args)
            deviceList.extend(driver.getDevices(silent, retry))
    return deviceList


def getHostPlatform(tempdir, args):
    if os.name == "nt":
        return WindowsPlatform(tempdir)
    else:
        return HostPlatform(tempdir, args)
