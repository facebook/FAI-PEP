from __future__ import absolute_import, division, print_function, unicode_literals

import unittest
import logging
import json
import sys
from os.path import expanduser
from unittest.mock import patch
import shutil


sys.path.append(".")
from benchmarking.run_bench import RunBench

class BasicFlowTest(unittest.TestCase):
    test_framework = "test/test_framework"
    test_remote_reporter = "test_remote_reporter"
    test_remote_access_token = "test_token"
    test_root_model_dir = "test/test_root_model_dir"
    test_report_to_screen = "Y"
    git_config = expanduser("~")  + '/.aibench/git'

    def setUp(self, *args, **kwargs):
        self.app = RunBench()

    def mock_args_input(self, key_str):
        if "framework repo" in key_str:
            return self.test_framework
        if "remote reporter" in key_str:
            return self.test_remote_reporter
        if "remote access token" in key_str:
            return self.test_remote_access_token
        if "root model dir" in key_str:
            return self.test_root_model_dir
        if "print report to screen" in key_str:
            return self.test_report_to_screen
        # should not come here
        self.assertRaise("unrecognized argument is provided")

    def repo_driver_command_checker(self, command):
        commands = command.split()
        self.assertEqual(
                commands[commands.index("--repo_dir") + 1],
                self.test_framework)
        self.assertEqual(
                commands[commands.index("--remote_reporter") + 1],
                self.test_remote_reporter)
        self.assertEqual(
                commands[commands.index("--remote_access_token") + 1],
                self.test_remote_access_token)
        self.assertEqual(
                commands[commands.index("--root_model_dir") + 1],
                self.test_root_model_dir)
        self.assertGreater(
                commands.index("--screen_reporter"),
                -1)
    def save_args_checker(self):
        # git_config
        with open(self.git_config + '/config.txt') as f:
            commands = json.load(f)

        self.assertEqual(
                commands["--repo_dir"],
                self.test_framework)
        self.assertEqual(
                commands["--remote_reporter"],
                self.test_remote_reporter)
        self.assertEqual(
                commands["--remote_access_token"],
                self.test_remote_access_token)
        self.assertEqual(
                commands["--root_model_dir"],
                self.test_root_model_dir)

    def test_benchmark_repo_driver_cmd_gen(self):
        with patch('six.moves.input', side_effect=self.mock_args_input):
            with patch('os.system', side_effect=self.repo_driver_command_checker):
                self.app.run()
                self.save_args_checker()
                shutil.rmtree(self.git_config)

if __name__ == '__main__':
    logger = logging.getLogger("AIBench")
    logger.setLevel(logging.DEBUG)
    try:
        unittest.main()
    except Exception as e:
        print(e)
