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
import copy
import json
import os
import six
import sys

from repo_driver import RepoDriver
from utils.custom_logger import getLogger
from utils.utilities import getString, getRunStatus, setRunStatus

parser = argparse.ArgumentParser(description="Perform one benchmark run")
parser.add_argument("--config_dir",
    default=os.path.join(os.path.expanduser('~'), ".aibench", "git"),
    help="Specify the config root directory.")
parser.add_argument("--reset_options", action="store_true",
    help="Reset all the options that is saved by default.")


class RunBench(object):
    def __init__(self):
        self.args, self.unknowns = parser.parse_known_args()
        self.root_dir = self.args.config_dir

    def run(self):
        raw_args = self._getRawArgs()
        app = RepoDriver(raw_args=raw_args)
        ret = app.run()
        setRunStatus(ret >> 8)
        sys.exit(getRunStatus())

    def _getUnknownArgs(self):
        unknowns = self.unknowns
        args = {}
        i = 0
        while i < len(unknowns):
            if len(unknowns[i]) > 2 and unknowns[i][:2] == '--':
                if i < len(unknowns) - 1 and unknowns[i + 1][:2] != '--':
                    args[unknowns[i]] = unknowns[i + 1]
                    i = i + 1
                else:
                    args[unknowns[i]] = None
            else:
                # error conditionm, skipping
                pass
            i = i + 1
        return args

    def _saveDefaultArgs(self, new_args):
        if not os.path.isdir(self.root_dir):
            os.makedirs(self.root_dir)
        args = {
            '--remote_repository': 'origin',
            '--commit': 'master',
            '--commit_file': os.path.join(self.root_dir, "processed_commit"),
            '--exec_dir': os.path.join(self.root_dir, "exec"),
            '--framework': 'caffe2',
            '--local_reporter': os.path.join(self.root_dir, "reporter"),
            '--repo': 'git',
            '--status_file': os.path.join(self.root_dir, "status"),
            '--model_cache': os.path.join(self.root_dir, "model_cache"),
            '--platforms': 'android',
            '--timeout': 300,
        }
        config_file = os.path.join(self.root_dir, "config.txt")
        if os.path.isfile(config_file):
            with open(config_file, "r") as f:
                load_args = json.load(f)
                args.update(load_args)
        args.update(new_args)
        self._inputOneRequiredArg(
            "Please enter the directory the framework repo resides",
            "--repo_dir", args)
        self._inputOneArg('Please enter the remote reporter',
                          "--remote_reporter", args)
        self._inputOneArg("Please enter the remote access token",
                          "--remote_access_token", args)
        self._inputOneArg("Please enter the root model dir if needed",
                          "--root_model_dir", args)
        self._inputOneArg("Do you want to print report to screen?",
                          "--screen_reporter", args)

        if not os.path.isfile(args['--status_file']):
            with open(args['--status_file'], 'w') as f:
                f.write("1")
        if "--screen_reporter" in args:
            args["--screen_reporter"] = None
        all_args = copy.deepcopy(args)
        if "--benchmark_file" in args:
            del args["--benchmark_file"]
        if "-b" in args:
            del args["-b"]
        with open(os.path.join(self.root_dir, "config.txt"), "w") as f:
            json_args = json.dumps(args,
                                   indent=2, sort_keys=True)
            f.write(json_args)
        return all_args

    def _inputOneArg(self, text, key, args):
        arg = args[key] if key in args else None
        v = six.moves.input(text + ' [' + str(arg) + ']: ')
        if v == '':
            v = arg
        if v is not None:
            args[key] = v
        return v

    def _inputOneRequiredArg(self, text, key, args):
        v = None
        while v is None:
            v = self._inputOneArg(text, key, args)
        return v

    def _getSavedArgs(self):
        new_args = self._getUnknownArgs()
        if self.args.reset_options or \
                not os.path.isdir(self.root_dir) or \
                not os.path.isfile(os.path.join(self.root_dir, "config.txt")):
            args = self._saveDefaultArgs(new_args)
        else:
            with open(os.path.join(self.root_dir, "config.txt"), "r") as f:
                args = json.load(f)
        for v in new_args:
            if v in args:
                del args[v]
        return args

    def _getRawArgs(self):
        args = self._getSavedArgs()
        raw_args = []
        for u in args:
            raw_args.extend([getString(u),
                getString(args[u]) if args[u] is not None else ""])
        raw_args.extend([getString(u) for u in self.unknowns])
        return raw_args


if __name__ == "__main__":
    app = RunBench()
    app.run()
