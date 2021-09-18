#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

# import os
# import sys
import unittest

import driver.benchmark_driver as bd


class BenchmarkDriverUnitTest(unittest.TestCase):
    def setUp(self):
        return

    log_prefix = "ERROR:GlobalLogger:"

    array1 = [0.0, 1.0, 2.0, 3.0, 4.0]

    array2 = [4.0, 3.0, 2.0, 1.0, 0.0]

    expected1 = {
        "mean": 2.0,
        "p0": 0.0,
        "p10": 0.4,
        "p50": 2.0,
        "p90": 3.6,
        "p100": 4.0,
        "stdev": 1.4142135623730951,
        "MAD": 1.0,
        "cv": 0.7071067811865476,
    }

    expected2 = {
        "mean": 2.0,
        "p0": 0.0,
        "p10": 0.4,
        "p50": 2.0,
        "p90": 3.6,
        "p100": 4.0,
        "stdev": 1.4142135623730951,
        "MAD": 1.0,
        "cv": 0.7071067811865476,
    }

    def test_getStatistics1(self):
        self.assertEqual(bd._getStatistics(self.array1), self.expected1)

    def test_getStatistics2(self):
        self.assertEqual(bd._getStatistics(self.array2), self.expected2)

    def test_getStatistics_custom_valid(self):
        stats = ["p10", "p90", "p50", "p95", "p5", "p11"]

        expected = {
            "p10": 0.4,
            "p11": 0.44,
            "p5": 0.2,
            "p50": 2.0,
            "p90": 3.6,
            "p95": 3.8,
        }

        self.assertEqual(bd._getStatistics(self.array1, stats), expected)

    def test_getStatistics_custom_missing_p50(self):
        stats = ["p10", "p90", "p95", "p5", "p11"]

        expected = {
            "p10": 0.4,
            "p11": 0.44,
            "p5": 0.2,
            "p90": 3.6,
            "p95": 3.8,
            "p50": 2.0,
        }

        self.assertEqual(bd._getStatistics(self.array1, stats), expected)

    def test_getStatistics_custom_padf(self):
        stats = ["padf"]

        with self.assertLogs(level="ERROR") as log:
            self.assertRaises(AssertionError, bd._getStatistics, self.array1, stats)
            self.assertIn(
                self.log_prefix
                + "Unsupported custom statistic '{}' ignored.".format(stats[0]),
                log.output,
            )

    def test_getStatistics_custom_p(self):
        stats = ["p"]
        with self.assertLogs(level="ERROR") as log:
            self.assertRaises(AssertionError, bd._getStatistics, self.array1, stats)
            self.assertIn(
                self.log_prefix
                + "Unsupported custom statistic '{}' ignored.".format(stats[0]),
                log.output,
            )

    def test_createDiffOfDelay1(self):
        expectedDiff = {
            "mean": 0.0,
            "p0": -4.0,
            "p10": -3.2,
            "p50": 0.0,
            "p90": 3.2,
            "p100": 4.0,
            "stdev": 0.0,
            "MAD": 0.0,
            "cv": 0.0,
        }

        self.assertEqual(
            bd._createDiffOfDelay(self.expected1, self.expected1), expectedDiff
        )

    def test_getPercentile_EmptyError(self):
        percentile = 50
        self.assertRaises(AssertionError, bd._getPercentile, [], percentile)

    def test_getPercentile_HighError(self):
        percentile = 106.1
        self.assertRaises(AssertionError, bd._getPercentile, self.array1, percentile)

    def test_getPercentile_LowError(self):
        percentile = -1
        self.assertRaises(AssertionError, bd._getPercentile, self.array1, percentile)


if __name__ == "__main__":
    unittest.main()
