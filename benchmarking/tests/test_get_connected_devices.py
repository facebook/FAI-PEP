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
import os
import sys
import unittest

from mock import patch

BENCHMARK_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir)
)
sys.path.append(BENCHMARK_DIR)
from get_connected_devices import GetConnectedDevices


class GetConnectedDevicesTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_run(self):
        config_path = os.path.join(BENCHMARK_DIR, "test/test_config")
        with patch(
            "get_connected_devices.getPlatforms", return_value=[]
        ) as getPlatforms, patch(
            "argparse.ArgumentParser.parse_known_args",
            return_value=(
                argparse.Namespace(
                    config_dir=config_path, logger_level="warn", reset_options=None
                ),
                [],
            ),
        ):
            app = GetConnectedDevices()
            app.run()
            getPlatforms.assert_called_once()


if __name__ == "__main__":
    unittest.main()
