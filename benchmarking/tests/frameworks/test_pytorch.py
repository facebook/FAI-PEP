##############################################################################
# Copyright 2025-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

# pyre-strict


import json
import os
import shutil
import tempfile
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

from frameworks.pytorch.pytorch import PytorchFramework
from utils.utilities import setRunStatus


def observer_row(
    value: float, metric: str = "latency", prefix: str = "PyTorchObserver "
) -> str:
    payload = json.dumps(
        {"type": "NET", "metric": metric, "unit": "ms", "value": str(value)}
    )
    return f"{prefix}{payload}"


class PytorchFrameworkTest(unittest.TestCase):
    def setUp(self) -> None:
        tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tempdir, ignore_errors=True)
        self.tempdir = tempdir
        self.framework = PytorchFramework(tempdir, args=None)
        self.platform = MagicMock()
        self.meta = {"platform": "host"}

    def _setOutputs(self, *outputs: Any) -> None:
        self.platform.runBenchmark.side_effect = [
            (output, self.meta) for output in outputs
        ]

    def _runOnPlatform(
        self, total_num: int, converter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return self.framework.runOnPlatform(
            total_num,
            ["run_benchmark"],
            self.platform,
            {"platform": "host"},
            converter,
        )

    def _latencies(self, metric: Dict[str, Any]) -> List[float]:
        return metric["NET latency"]["values"]

    def test_working_directory_is_named_after_the_framework(self) -> None:
        self.assertEqual(self.framework.getName(), "pytorch")
        self.assertTrue(os.path.isdir(os.path.join(self.tempdir, "pytorch")))

    def test_default_converter_collects_only_rows_with_pytorch_identifier(self) -> None:
        self._setOutputs(
            "\n".join(
                [
                    "an unrelated benchmark log line",
                    observer_row(99, prefix="Caffe2Observer "),
                    observer_row(10),
                    observer_row(20),
                ]
            )
        )

        metric = self._runOnPlatform(total_num=2)

        self.assertEqual(self._latencies(metric), [10.0, 20.0])
        self.assertEqual(metric["meta"], self.meta)
        self.platform.runBenchmark.assert_called_once_with(
            ["run_benchmark"], platform_args={"platform": "host"}
        )

    def test_runs_again_until_total_num_results_are_collected(self) -> None:
        self._setOutputs(observer_row(10), observer_row(20), observer_row(30))

        metric = self._runOnPlatform(total_num=3)

        self.assertEqual(self._latencies(metric), [10.0, 20.0, 30.0])
        self.assertEqual(self.platform.runBenchmark.call_count, 3)

    def test_stops_running_when_no_new_results_are_collected(self) -> None:
        self._setOutputs("no parsable observer output in here")

        metric = self._runOnPlatform(total_num=2)

        self.assertEqual(dict(metric), {"meta": self.meta})
        self.platform.runBenchmark.assert_called_once()

    def test_extra_results_are_trimmed_to_the_latest_entries(self) -> None:
        self._setOutputs("\n".join([observer_row(10), observer_row(20)]))

        metric = self._runOnPlatform(total_num=1)

        self.assertEqual(self._latencies(metric), [20.0])

    def test_explicit_converter_skips_identifier_filtering(self) -> None:
        self._setOutputs("\n".join([observer_row(30, prefix=""), observer_row(40)]))

        metric = self._runOnPlatform(total_num=2, converter={"name": "json_converter"})

        self.assertEqual(self._latencies(metric), [30.0, 40.0])

    def test_keeps_collecting_after_a_failed_run(self) -> None:
        setRunStatus(1)
        self.addCleanup(setRunStatus, 0, True)
        self._setOutputs(observer_row(10), observer_row(20))

        metric = self._runOnPlatform(total_num=2)

        self.assertEqual(self._latencies(metric), [10.0, 20.0])
        self.assertEqual(self.platform.runBenchmark.call_count, 2)
