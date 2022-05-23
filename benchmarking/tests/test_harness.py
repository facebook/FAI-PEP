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
import json
import os
import sys
import unittest

from unittest.mock import patch

BENCHMARK_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir)
)
sys.path.append(BENCHMARK_DIR)
from harness import BenchmarkDriver


class BenchmarkDriverTest(unittest.TestCase):
    def setUp(self):
        info_path = os.path.join(BENCHMARK_DIR, "test/test_config/info.json")
        info = json.load(open(info_path, "r"))
        self.info = str(info).replace("'", '"')
        self.args = argparse.Namespace(
            benchmark_file=os.path.join(
                BENCHMARK_DIR,
                "../specifications/models/caffe2/squeezenet/squeezenet.json",
            ),
            framework="caffe2",
            info=self.info,
            model_cache="e",
            platform="host",
            command_args="e",
            backend="e",
            wipe_cache="False",
            user_string="test",
            debug=False,
        )

    def test_run(self):
        with patch(
            "harness.parseKnown", return_value=(argparse.Namespace(), [])
        ), patch("harness.getArgs", return_value=self.args), patch(
            "harness.BenchmarkCollector.collectBenchmarks", return_value=[]
        ), patch(
            "harness.getPlatforms", return_value=[]
        ):
            app = BenchmarkDriver()
            app.run()
            status = app.status
            self.assertEqual(status, 0)


if __name__ == "__main__":
    unittest.main()
