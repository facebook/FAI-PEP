#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


import argparse
import json
import os
import sys
import tempfile
import unittest

from unittest.mock import patch

BENCHMARK_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)), os.pardir, os.pardir, os.pardir
    )
)
sys.path.append(BENCHMARK_DIR)

from platforms.ios.idb import IDB
from platforms.ios.ios_platform import IOSPlatform


class IOSPlatformTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp(prefix="aibench")
        device = {"12345678-9012345678AB901C": "A012BC"}
        idb = IDB(device, self.tempdir)
        with patch("platforms.ios.ios_platform.IOSPlatform.setPlatformHash"), patch(
            "platforms.ios.ios_platform.getArgs",
            return_value=argparse.Namespace(ios_dir=self.tempdir),
        ), patch(
            "platforms.platform_base.getArgs",
            return_value=argparse.Namespace(hash_platform_mapping=None),
        ):
            self.platform = IOSPlatform(self.tempdir, idb)

    def _list_dir_for_preprocess(self, app_dir):
        self.assertEqual(app_dir, self.tempdir + "/Payload")
        return ["TestDir.app"]

    def _process_run_for_preprocess(self, args):
        app = self.tempdir + "/Payload/TestDir.app"
        self.assertTrue(
            args == ["osascript", "-e", 'id of app "' + app + '"']
            or args == ["unzip", "-o", "-d", self.tempdir, "test_program.ipa"]
        )
        return ["com.facebook.test"], ""

    def _set_bundle_id_for_preprocess(self, bundle_id):
        self.assertEqual(bundle_id, "com.facebook.test")

    def _idb_run_for_preprocess(self, args):
        app = self.tempdir + "/Payload/TestDir.app"
        self.assertEqual(args, ["--bundle", app, "--uninstall"])

    def test_preprocess(self):
        programs = {"program": "test_program.ipa"}
        with patch(
            "platforms.ios.ios_platform.processRun",
            side_effect=self._process_run_for_preprocess,
        ), patch("os.listdir", side_effect=self._list_dir_for_preprocess), patch(
            "os.path.isdir", return_value=True
        ), patch(
            "platforms.ios.idb.IDB.run", side_effect=self._idb_run_for_preprocess
        ), patch(
            "platforms.ios.idb.IDB.setBundleId",
            side_effect=self._set_bundle_id_for_preprocess,
        ):
            self.platform.preprocess(programs=programs)

    def _push_for_run_benchmark(self, src, tgt):
        sample = open("test_argument_file.json")
        sample_data = json.load(sample)

        test = open(src)
        test_data = json.load(test)

        self.assertEqual(sample_data, test_data)

        sample.close()
        test.close()

    def _idb_run_for_run_benchmark(self, *args, **kwargs):
        expected_cmd = [
            "--bundle",
            None,
            "--noninteractive",
            "--noinstall",
            "--unbuffered",
            "--args",
            "--input_dims 1,3,224,224 --warmup 1 --input_type "
            "float --iter 50 --run_individual true --init_net "
            "/tmp/init_net.pb --input data --net "
            "/tmp/predict_net.pb",
        ]
        self.assertEqual(args[0], expected_cmd)
        return True

    def test_run_benchmark(self):
        self.platform.util.setBundleId("com.facebook.test")
        cmd = (
            "{program} --net /tmp/predict_net.pb --init_net /tmp/init_net.pb "
            '--warmup 1 --iter 50 --input "data" --input_dims "1,3,224,224" '
            "--input_type float --run_individual true"
        )

        with patch(
            "platforms.ios.idb.IDB.push", side_effect=self._push_for_run_benchmark
        ), patch(
            "platforms.ios.idb.IDB.run", side_effect=self._idb_run_for_run_benchmark
        ):
            res = self.platform.runBenchmark(cmd, platfor_args={"timeout": 300.0})
            self.assertTrue(res)


if __name__ == "__main__":
    unittest.main()
