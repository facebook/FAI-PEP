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
import os
import sys
import threading
import unittest
from collections import deque

from mock import patch

BENCHMARK_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir)
)
sys.path.append(BENCHMARK_DIR)
from repo_driver import ExecutablesBuilder, RepoDriver
from repos.git import GitRepo


class RepoDriverTest(unittest.TestCase):
    def setUp(self):
        self.args = argparse.Namespace(
            exec_dir=os.path.join(BENCHMARK_DIR, "test/test_config"),
            repo="git",
            repo_dir="/test/pytorch",
            interval=0,
            same_host=True,
            platforms="host",
            status_file=os.path.join(BENCHMARK_DIR, "test/test_config/status"),
            regression=False,
            ab_testing=False,
            frameworks_dir=BENCHMARK_DIR,
            framework="test",
            env=None,
            commit_file="/test/.aibench/git/processed_commit",
            benchmark_file=os.path.join(
                BENCHMARK_DIR,
                "../specifications/models/caffe2/squeezenet/squeezenet.json",
            ),
            model_cache="/test/.aibench/git/model_cache",
        )

    def test_run(self):
        class mock_thread(object):
            def is_alive(self):
                return False

        with patch(
            "repo_driver.parseKnown", return_value=(argparse.Namespace(), [])
        ), patch("repo_driver.getArgs", return_value=self.args), patch(
            "repo_driver.getRepo", return_value=GitRepo("/test/pytorch")
        ), patch(
            "repo_driver.ExecutablesBuilder._setupRepoStep",
            return_value={"commit": "123"},
        ), patch(
            "os.system", return_value=1
        ):
            app = RepoDriver()
            app.run()

    def test_buildProgram(self):
        with patch(
            "repo_driver.parseKnown", return_value=(argparse.Namespace(), [])
        ), patch("repo_driver.getArgs", return_value=self.args), patch(
            "repo_driver.getRepo", return_value=GitRepo("/test/pytorch")
        ), patch(
            "repo_driver.ExecutablesBuilder._buildProgramPlatform", return_value=None
        ), patch(
            "os.listdir", return_value=os.path.join(BENCHMARK_DIR, "test/test_config")
        ):
            app = ExecutablesBuilder(
                GitRepo("/test/pytorch"), threading.Lock(), deque()
            )
            app._buildProgram("host", {"commit": "123", "commit_time": 123})

    def test_getControlCommit(self):
        with patch(
            "repo_driver.parseKnown", return_value=(argparse.Namespace(), [])
        ), patch("repo_driver.getArgs", return_value=self.args), patch(
            "repos.git.GitRepo.getCommitsInRange", return_value="1:2\n3:4"
        ):
            app = ExecutablesBuilder(
                GitRepo("/test/pytorch"), threading.Lock(), deque()
            )
            app._getControlCommit(reference_time=123, base_commit=None)


if __name__ == "__main__":
    unittest.main()
