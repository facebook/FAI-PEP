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
import argparse
from mock import patch
import unittest
import os
import sys

BENCHMARK_DIR = os.path.abspath(os.path.join(
                                os.path.dirname(os.path.realpath(__file__)), os.pardir))
sys.path.append(BENCHMARK_DIR)
from reboot_device import reboot


class RebootTest(unittest.TestCase):

    def setUp(self):
        pass

    def test_reboot(self):
        with patch("reboot_device.parse",
                return_value=(argparse.Namespace(), [])),\
                patch("reboot_device.getArgs",
                return_value=argparse.Namespace(
                device="ios", platform="ios")) as mock_ios:
            reboot()
            self.assertEqual(mock_ios.call_count, 2)

        with patch("reboot_device.parse",
                return_value=(argparse.Namespace(), [])),\
                patch("reboot_device.getArgs",
                return_value=argparse.Namespace(
                device="android", platform="android")) as mock_ios:
            reboot()
            self.assertEqual(mock_ios.call_count, 2)

        with patch("reboot_device.parse",
                return_value=(argparse.Namespace(), [])),\
                patch("reboot_device.getArgs",
                return_value=argparse.Namespace(
                device="UNKNOWN", platform="UNKNOWN")) as mock_ios:
            try:
                reboot()
            except AssertionError as e:
                print(str(e))
                self.assertEqual(str(e), "Platform UNKNOWN not recognized")


if __name__ == "__main__":
    unittest.main()
