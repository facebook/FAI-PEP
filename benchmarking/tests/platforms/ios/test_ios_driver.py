#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


import argparse
import os
import sys
import unittest
from unittest.mock import patch

BENCHMARK_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)), os.pardir, os.pardir, os.pardir
    )
)
sys.path.append(BENCHMARK_DIR)

from platforms.ios.ios_driver import IOSDriver


class IOSDriverTest(unittest.TestCase):
    def setUp(self):
        pass

    def _idb_run_for_get_device(self, *args):
        return [
            "[....] Waiting up to 5 seconds for iOS device to be connected",
            "[....] Found 12345678-9012345678AB901C (A012BC, A012BC, "
            "uknownos, unkarch) a.k.a. 'Developer iPhone' connected "
            "through USB.",
        ]

    def test_get_devices(self):
        driver = IOSDriver()
        with patch(
            "platforms.ios.idb.IDB.run", side_effect=self._idb_run_for_get_device
        ):
            devices = driver.getDevices()
            self.assertEqual(devices, {"12345678-9012345678AB901C": "A012BC"})

    def test_get_ios_platforms(self):
        driver = IOSDriver()
        with (
            patch(
                "platforms.ios.ios_driver.IOSDriver.getDevices",
                return_value={"12345678-9012345678AB901C": "A012BC"},
            ),
            patch("platforms.ios.ios_platform.IOSPlatform.__init__", return_value=None),
            patch(
                "platforms.ios.ios_platform.IOSPlatform.setPlatform", return_value=None
            ),
            patch(
                "platforms.ios.ios_driver.getArgs",
                return_value=argparse.Namespace(
                    device=None, devices=None, excluded_devices=None
                ),
            ),
        ):
            platforms = driver.getIOSPlatforms("/tmp")
            self.assertEqual(len(platforms), 1)
            self.assertTrue(platforms[0])


if __name__ == "__main__":
    unittest.main()
