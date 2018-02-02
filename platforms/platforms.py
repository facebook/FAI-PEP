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


def getPlatforms():
    platforms = []
    if getArgs().host:
        platforms.append(HostPlatform())
    if getArgs().android:
        driver = AndroidDriver()
        platforms.extend(driver.getAndroidPlatforms())
    if getArgs().excluded_platforms:
        excluded_platforms = getArgs().excluded_platforms.strip().split(',')
        platforms = \
            [p for p in platforms if p.platform not in excluded_platforms and
             (p.platform_hash is None or
              p.platform_hash not in excluded_platforms)]
    if getArgs().platforms:
        plts = getArgs().platforms.strip().split(',')
        platforms = [p for p in platforms if p.platform in plts or
                     p.platform_hash in plts]
    if not platforms:
        getLogger().error("No platform is specified.")
    return platforms
