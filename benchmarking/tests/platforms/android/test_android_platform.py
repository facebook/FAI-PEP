#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import os
import sys
import tempfile
import unittest

from unittest.mock import Mock, patch

BENCHMARK_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)), os.pardir, os.pardir, os.pardir
    )
)
sys.path.append(BENCHMARK_DIR)

from platforms.android.adb import ADB
from platforms.android.android_platform import AndroidPlatform


class AndroidPlatformTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp(prefix="aibench")
        self.model = "Drone-DEV"
        device = {"12345678-9012345678AB901C": self.model}
        self.adb = ADB(device, self.tempdir)

        def mock_getprop(key):
            ret = {
                "ro.build.version.release": "12",
                "ro.build.version.sdk": "30",
                "ro.product.model": self.model,
                "ro.product.cpu.abi": "arm64",
                "ro.build.version.incremental": "1234567",
            }
            return ret[key]

        self.adb.getprop = Mock(side_effect=mock_getprop)
        self.adb.logcat = Mock(return_value="success")
        self.adb.shell = Mock()
        self.args = argparse.Namespace(
            android_dir=self.tempdir,
            device_name_mapping=None,
            hash_platform_mapping=None,
            set_freq=False,
        )

    def test_thermal_monitoring(self):
        mock_thermal_monitor_config = {
            "Drone-DEV": {
                "script": "specifications/platform_scripts/thermal_monitoring/android_thermal_monitor.sh",
                "trip_temp_expr": "32000",
                "temp_probe": "/path/to/thermal/zone/temp",
            }
        }
        mock_json_loads_thermal_monitor = Mock(return_value=mock_thermal_monitor_config)
        with patch(
            "platforms.android.android_platform.json.loads",
            side_effect=mock_json_loads_thermal_monitor,
        ), patch("platforms.android.android_platform.pkg_resources.resource_string"):
            self.platform = AndroidPlatform(self.tempdir, self.adb, self.args)
            self.assertEqual(
                self.platform.thermal_monitor_config,
                mock_thermal_monitor_config[self.model],
            )


if __name__ == "__main__":
    unittest.main()
