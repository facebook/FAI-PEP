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

BENCHMARK_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, os.pardir)
)
sys.path.append(BENCHMARK_DIR)

from run_bench import RunBench


class RunBenchUnitTest(unittest.TestCase):
    def setUp(self):
        self.app = RunBench()

    def test_getUnknownArgs(self):
        self.app.unknowns = "--remote -b /home/mobilenet_v3.json\
                             --platform android --framework pytorch\
                             --devices SM-G981U1-11-30 --buck_target".split()
        expected = {
            "--remote": None,
            "-b": "/home/mobilenet_v3.json",
            "--platform": "android",
            "--framework": "pytorch",
            "--devices": "SM-G981U1-11-30",
            "--buck_target": None,
        }
        self.assertEqual(self.app._getUnknownArgs(), expected)

        self.app.unknowns = "--remote True -b --platform android\
                             --framework pytorch --devices SM-G981U1-11-30\
                             Pixel_5 --buck_target".split()
        expected = {
            "--remote": "True",
            "-b": None,
            "--platform": "android",
            "--framework": "pytorch",
            "--devices": "SM-G981U1-11-30",
            "--buck_target": None,
        }
        self.assertEqual(self.app._getUnknownArgs(), expected)

        self.app.unknowns = "--remote -b --platform\
                             --framework -d --buck_target -c -e".split()
        expected = {
            "--remote": None,
            "-b": None,
            "--platform": None,
            "--framework": None,
            "-d": None,
            "--buck_target": None,
            "-c": None,
            "-e": None,
        }
        self.assertEqual(self.app._getUnknownArgs(), expected)

        self.app.unknowns = "--remote -b --platform android\
                             --framework pytorch --devices\
                             SM-G981U1-11-30,Pixel_5 SM-A530W-9-28".split()
        expected = {
            "--remote": None,
            "-b": None,
            "--platform": "android",
            "--framework": "pytorch",
            "--devices": "SM-G981U1-11-30,Pixel_5",
        }
        self.assertEqual(self.app._getUnknownArgs(), expected)


if __name__ == "__main__":
    unittest.main()
