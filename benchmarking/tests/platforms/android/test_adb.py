#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


import os
import sys
import unittest
from unittest.mock import Mock

BENCHMARK_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)), os.pardir, os.pardir, os.pardir
    )
)
sys.path.append(BENCHMARK_DIR)

from platforms.android.adb import ADB


class ADBTest(unittest.TestCase):
    def setUp(self):
        self.adb = ADB()
        self.adb.user_is_root = Mock(return_value=True)

    def test_getBatteryProp_returns_value_when_file_exists(self):
        self.adb.shell = Mock(return_value=["1"])
        self.assertEqual(self.adb.getBatteryProp("present"), "1")
        self.adb.shell.assert_called_once_with(
            ["cat", "/sys/class/power_supply/battery/present"],
            retry=1,
            silent=True,
        )

    def test_getBatteryProp_returns_empty_string_when_file_missing(self):
        # A missing sysfs entry makes the adb shell command fail with no
        # output; previously this raised IndexError instead of returning "".
        self.adb.shell = Mock(return_value=[])
        self.assertEqual(self.adb.getBatteryProp("present"), "")

    def test_getBatteryProp_returns_empty_string_when_not_root(self):
        self.adb.user_is_root = Mock(return_value=False)
        self.adb.shell = Mock()
        self.assertEqual(self.adb.getBatteryProp("present"), "")
        self.adb.shell.assert_not_called()


if __name__ == "__main__":
    unittest.main()
