##############################################################################
# Copyright 2022-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import unittest
from unittest.mock import Mock

from platforms.platform_base import PlatformBase


class PlatformBaseTest(unittest.TestCase):
    def setUp(self):
        platform_util = Mock()
        platform_util.device = "hash"
        self.platform = PlatformBase(None, None, platform_util, None, None)

    def test_get_paired_arguments(self):
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
