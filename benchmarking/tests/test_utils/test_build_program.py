#!/usr/bin/env python

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
from tempfile import gettempdir

from unittest.mock import patch

BENCHMARK_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, os.pardir)
)
sys.path.append(BENCHMARK_DIR)

from utils.build_program import _isBuildSuccessful, _setUpTempDirectory, buildUsingBuck


class BuildProgramTest(unittest.TestCase):
    def setUp(self):
        self.fake_file = os.path.join(gettempdir(), "aibenchtest1", "test")
        self.actual_file = os.path.join(gettempdir(), "aibenchtest2", "program")
        _setUpTempDirectory(self.actual_file)
        with open(self.actual_file, "a"):
            os.utime(self.actual_file, None)

    def testBuckBuild(self):
        with patch(
            "utils.subprocess_with_logger.processRun",
            return_value=("Build was unsuccessful", [Exception()]),
        ):
            self.assertFalse(buildUsingBuck(self.fake_file, "android", "buck"))
        with patch(
            "utils.subprocess_with_logger.processRun",
            return_value=("Build was successful", []),
        ), patch("utils.build_program._setUpTempDirectory"):
            self.assertTrue(buildUsingBuck(self.actual_file, "ios", "buck"))

    def testisBuildSuccessful(self):
        self.assertFalse(
            _isBuildSuccessful(self.fake_file, "ios", "buck build aibench:run")
        )
        self.assertTrue(
            _isBuildSuccessful(self.actual_file, "oculus", "buck build aibench:run")
        )


if __name__ == "__main__":
    unittest.main()
