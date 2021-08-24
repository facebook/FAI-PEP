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
import json
import os
import shutil
import sys
import unittest

from mock import patch

BENCHMARK_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir)
)
sys.path.append(BENCHMARK_DIR)
from run_bench import RunBench


class RunBenchTest(unittest.TestCase):
    def setUp(self):
        self.python = sys.executable
        self.repo_driver = os.path.join(BENCHMARK_DIR, "repo_driver.py")
        self.app = RunBench()
        self.params = {
            "--app_id": "123",
            "--benchmarking_dir": "/test/caffe2-benchmarking",
            "--cache_config": "/test/.aibench/git/cache_config.txt",
            "--commit": "master",
            "--commit_file": "/test/.aibench/git/processed_commit",
            "--exec_dir": "/test/.aibench/git/exec",
            "--framework": "caffe2",
            "--frameworks_dir": "/test/aibench/specifications/frameworks",
            "--job_queue": "aibench_interactive",
            "--local_reporter": "/test/.aibench/git/reporter",
            "--model_cache": "/test/.aibench/git/model_cache",
            "--platform": "android",
            "--platforms": "android",
            "--remote_access_token": "456",
            "--remote_reporter": "perfpipe",
            "--remote_repository": "origin",
            "--repo": "git",
            "--repo_dir": "/test/pytorch",
            "--root_model_dir": "/test/.aibench/git/root_model_dir",
            "--screen_reporter": None,
            "--status_file": "/test/.aibench/git/status",
            "--timeout": "300",
            "--token": "ABC",
            "--logger_level": "warn",
            "--unknown1": "UNKNOWN1",
            "--unknown2": "UNKNOWN2",
            "--lab": None,
        }
        self.input_args = {
            "--remote_reporter": "a",
            "--remote": True,
            "--repo_dir": "b",
            "--app_id": "1",
            "--token": "ABC",
            "--job_queue": "aibench",
            "--remote_access_token": "2",
            "--benchmarking_dir": "d",
            "--platform": "e",
            "--screen_reporter": None,
            "--root_model_dir": "/test/.aibench/git/root_model_dir",
        }

    def _check_repo_driver_call_params(self, cmd):
        cmds = cmd.split()
        self.assertEqual(cmds[0], self.python)
        self.assertEqual(cmds[1], self.repo_driver)

        for i in range(2, len(cmds)):
            if (
                cmds[i].startswith("--")
                and i + 1 < len(cmds)
                and not cmds[i + 1].startswith("--")
            ):
                self.assertEqual(cmds[i + 1], self.params[cmds[i]])
            elif cmds[i].startswith("--") and (
                i + 1 == len(cmds) or cmds[i + 1].startswith("--")
            ):
                self.assertEqual(None, self.params[cmds[i]])
        return 0

    def _mock_input_arg(self, text, key, args):
        args[key] = self.input_args[key]
        return self.input_args[key]

    def check_config_file_content(self, args):
        config_file = os.path.join(
            BENCHMARK_DIR, "test/test_home/.aibench/git/config.txt"
        )
        with open(config_file) as f:
            config_content = json.load(f)
            for key in [
                "--remote_reporter",
                "--remote_access_token",
                "--root_model_dir",
                "--screen_reporter",
            ]:
                self.assertEqual(config_content[key], args[key])

    def test_existing_config(self):
        config_path = os.path.join(BENCHMARK_DIR, "test/test_config")
        with patch(
            "os.system", side_effect=self._check_repo_driver_call_params
        ) as repo_driver, patch(
            "utils.arg_parse.parseKnown",
            return_value=(
                argparse.Namespace(
                    config_dir=config_path, logger_level="warn", reset_options=None
                ),
                [],
            ),
        ):
            self.app.root_dir = config_path
            self.app.run()
            repo_driver.assert_called_once()
        return

    def test_existing_config_unknows(self):
        config_path = os.path.join(BENCHMARK_DIR, "test/test_config")
        with patch(
            "os.system", side_effect=self._check_repo_driver_call_params
        ) as repo_driver, patch(
            "argparse.ArgumentParser.parse_known_args",
            return_value=(
                argparse.Namespace(
                    config_dir=config_path, logger_level="warn", reset_options=None
                ),
                ["--unknown1", "UNKNOWN1", "--unknown2", "UNKNOWN2"],
            ),
        ):
            self.app.root_dir = config_path
            self.app.run()
            repo_driver.assert_called_once()
        return

    def test_new_config(self):
        test_home = os.path.join(BENCHMARK_DIR, "test/test_home/.aibench/git")
        with patch("os.system", return_value=0) as repo_driver, patch(
            "run_bench.RunBench._inputOneArg", side_effect=self._mock_input_arg
        ), patch(
            "argparse.ArgumentParser.parse_known_args",
            return_value=(
                argparse.Namespace(
                    config_dir=None, logger_level="warn", reset_options=True
                ),
                ["--unknown1", "UNKNOWN1", "--unknown2", "UNKNOWN2"],
            ),
        ):
            self.app.root_dir = test_home
            self.app.run()
            repo_driver.assert_called_once()
            self.check_config_file_content(self.input_args)
            shutil.rmtree(test_home)
        return


if __name__ == "__main__":
    unittest.main()
