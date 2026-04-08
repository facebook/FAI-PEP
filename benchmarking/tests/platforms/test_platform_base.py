##############################################################################
# Copyright 2022-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

# pyre-strict


import unittest
from typing import Any, Optional, Tuple
from unittest.mock import Mock

from platforms.platform_base import PlatformBase


class ConcretePlatformBase(PlatformBase):
    """Concrete implementation of PlatformBase for testing purposes."""

    def getABI(self) -> str:
        return self.platform_abi or "null"

    def getKind(self) -> Optional[str]:
        return self.platform

    def getOS(self) -> None:
        pass

    def getName(self) -> str:
        if self.device_name_mapping and self.platform_model in self.device_name_mapping:
            return self.device_name_mapping[self.platform_model]
        else:
            return "null"

    def runBenchmark(self, cmd: Any, *args: Any, **kwargs: Any) -> Tuple[None, None]:
        return None, None

    def preprocess(self, *args: Any, **kwargs: Any) -> None:
        pass

    def postprocess(self, *args: Any, **kwargs: Any) -> None:
        pass

    def killProgram(self, program: Any) -> None:
        pass

    def waitForDevice(self) -> None:
        pass

    def currentPower(self) -> None:
        pass

    def cleanup(self) -> None:
        pass


class PlatformBaseTest(unittest.TestCase):
    platform: ConcretePlatformBase

    def setUp(self) -> None:
        platform_util = Mock()
        platform_util.device = "hash"
        self.platform = ConcretePlatformBase(None, None, platform_util, None, None)

    def test_get_paired_arguments(self) -> None:
        err_cmd = [
            "{program}",
            "--model",
            "/tmp/nlu_model_bundled.ptl",
            "--use_bundled_input=0",
            "--warmup",
            "10",
            "--iter",
            "50",
            "--report_pep",
            "true",
            "—use_caching_allocator",  # single -, invalid token
            "true",
        ]
        with self.assertRaisesRegex(
            RuntimeError,
            "Argument '—use_caching_allocator' could not be parsed from the command",
        ):
            self.platform.getPairedArguments(err_cmd)

        valid_cmd = [
            "{program}",
            "--model",
            "/tmp/nlu_model_bundled.ptl",
            "--use_bundled_input=0",
            "--warmup",
            "10",
            "--iter",
            "50",
            "--report_pep",
            "true",
            "--use_caching_allocator",
            "true",
        ]
        res = self.platform.getPairedArguments(valid_cmd)
        self.assertEqual(
            res,
            {
                "iter": "50",
                "model": "/tmp/nlu_model_bundled.ptl",
                "report_pep": "true",
                "use_bundled_input": "0",
                "use_caching_allocator": "true",
                "warmup": "10",
            },
        )


if __name__ == "__main__":
    unittest.main()
