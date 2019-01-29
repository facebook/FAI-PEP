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
from mock import patch
import unittest
import os
import sys

BENCHMARK_DIR = os.path.abspath(os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    os.pardir, os.pardir, os.pardir, os.pardir, 'benchmarking'))
sys.path.append(BENCHMARK_DIR)

from platforms.ios.idb import IDB


class IDBTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_set_bundle_id(self):
        idb = IDB()
        idb.setBundleId("TEST")
        self.assertEqual(idb.bundle_id, "TEST")

    def _util_base_run(self, *args, **kwargs):
        self.assertEqual(args[0], ["ios-deploy"])

    def test_run(self):
        idb = IDB()
        with patch("platforms.platform_util_base.PlatformUtilBase.run",
                   side_effect=self._util_base_run):
            idb.run()

    def _ios_run_for_push(self, *args, **kwargs):
        return args

    def test_push(self):
        src = os.path.abspath(os.path.join(
            BENCHMARK_DIR, os.pardir,
            "specifications/models/caffe2/squeezenet/squeezenet.json"))
        tgt = "TEST_TGT"
        idb = IDB()

        with patch("platforms.ios.idb.IDB.run",
                   side_effect=self._ios_run_for_push):
            push_res = idb.push(src, tgt)
            self.assertEqual(push_res, ("--upload", src, "--to", tgt))

    def _ios_run_for_reboot(self, *args, **kwargs):
        self.assertTrue(args[0] == "idevicepair" or
                        args[0] == "idvicediagnostics")
        self.assertEqual(args[1], "-u")
        self.assertEqual(args[2], "TEST_DEVICE")
        self.assertTrue(args[3] == "pair" or args[3] == "restart")

    def test_reboot(self):
        idb = IDB(device="TEST_DEVICE")
        with patch("platforms.ios.idb.IDB.run",
                   side_effect=self._ios_run_for_reboot):
            push_res = idb.reboot()
            self.assertTrue(push_res)


if __name__ == "__main__":
    unittest.main()
