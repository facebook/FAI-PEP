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

from lab_driver import LabDriver
from utils.custom_logger import getLogger, setLoggerLevel
from utils.utilities import getString, getRunStatus, setRunStatus


HOME_DIR = os.path.expanduser('~')
parser = argparse.ArgumentParser(description="Perform one benchmark run")
parser.add_argument("--config_dir",
    default=os.path.join(HOME_DIR, ".aibench", "git"),
    help="Specify the config root directory.")
parser.add_argument("--logger_level", default="info",
    choices=["info", "warning", "error"],
    help="Specify the logger level")
parser.add_argument("--reset_options", action="store_true",
    help="Reset all the options that is saved by default.")


class RunBench(object):
    def __init__(self, raw_args=None):
        self.args, self.unknowns = parser.parse_known_args(raw_args)
        self.root_dir = self.args.config_dir
        self.repoCls = LabDriver
        setLoggerLevel(self.args.logger_level)

    def run(self):
        raw_args = self._getRawArgs()
        if "--remote" in raw_args or "--lab" in raw_args:

            # server address must start with http
            assert "--server_addr" in raw_args
            idx = raw_args.index("--server_addr")
            assert raw_args[idx + 1].startswith("http") or len(raw_args[idx + 1]) == 0
        if "--lab" in raw_args and "--remote_reporter" not in raw_args:
            raw_args.extend(["--remote_reporter",
                raw_args["--server_addr"] + "/benchmark/store-result|oss"])
        app = self.repoCls(raw_args=raw_args)
        ret = app.run()
        if "--query_num_devices" in self.unknowns:
            return ret
        if "--fetch_status" in self.unknowns or "--fetch_result" in self.unknowns:
            return ret
        if ret is not None:
            setRunStatus(ret >> 8)
        return getRunStatus()

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

        print("Setting the default arguments...")
        print("The default arguments are saved under {}".
              format(self.root_dir + "/config.txt"))
        print("Alternatively, you can edit the config.txt file directly\n")
        args = self._loadDefaultArgs()

        config_file = os.path.join(self.root_dir, "config.txt")
        if os.path.isfile(config_file):
            with open(config_file, "r") as f:
                load_args = json.load(f)
                args.update(load_args)

        args = self._askArgsFromUser(args, new_args)

        if not os.path.isfile(args["--status_file"]):
            with open(args["--status_file"], "w") as f:
                f.write("1")
        if "--screen_reporter" in args:
            args["--screen_reporter"] = None
        all_args = copy.deepcopy(args)
        if "--benchmark_file" in args:
            del args["--benchmark_file"]
        if "-b" in args:
            del args["-b"]
        if "--devices" in args:
            del args["--devices"]
        with open(os.path.join(self.root_dir, "config.txt"), "w") as f:
            json_args = json.dumps(args,
                                   indent=2, sort_keys=True)
            f.write(json_args)

        return all_args

    def _askArgsFromUser(self, args, new_args):
        args.update(new_args)
        self._inputOneRequiredArg(
            "Please enter the directory the framework repo resides",
            "--repo_dir", args)
        self._inputOneArg("Please enter the remote reporter",
                          "--remote_reporter", args)
        self._inputOneArg("Please enter the remote access token",
                          "--remote_access_token", args)
        self._inputOneArg("Please enter the root model dir if needed",
                          "--root_model_dir", args)
        self._inputOneArg("Do you want to print report to screen?",
                          "--screen_reporter", args)
        return args

    def _loadDefaultArgs(self):
        args = {
            '--benchmark_table': 'benchmark_benchmarkinfo',
            '--cache_config': os.path.join(self.root_dir, "cache_config.txt"),
            '--remote_repository': 'origin',
            '--commit': 'master',
            '--commit_file': os.path.join(self.root_dir, "processed_commit"),
            '--exec_dir': os.path.join(self.root_dir, "exec"),
            '--framework': 'caffe2',
            '--local_reporter': os.path.join(self.root_dir, "reporter"),
            '--repo': 'git',
            '--root_model_dir': os.path.join(self.root_dir, "root_model_dir"),
            '--status_file': os.path.join(self.root_dir, "status"),
            '--model_cache': os.path.join(self.root_dir, "model_cache"),
            '--platform': 'android',
            '--file_storage': 'django',
            '--timeout': 300,
            '--logger_level': 'warning',
            '--server_addr': "http://127.0.0.1:8000",
            '--result_db': "django",
        }
        return args

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
        if "--lab" in new_args:
            if "--remote" in args:
                del args["--remote"]
        return args

    def _getRawArgs(self):
        args = self._getSavedArgs()
        raw_args = []
        for u in args:
            raw_args.extend([getString(u),
                getString(args[u]) if args[u] is not None else ""])
        raw_args.extend([getString(u) for u in self.unknowns])
        raw_args.extend(["--logger_level", self.args.logger_level])
        return raw_args


if __name__ == "__main__":
    raw_args = None
    app = RunBench(raw_args=raw_args)
    app.run()
