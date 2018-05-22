#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import copy
import json
import os
import re
from utils.arg_parse import getParser, getArgs, getUnknowns, parseKnown
from utils.custom_logger import getLogger

getParser().add_argument("--reset_options", action="store_true",
    help="Reset all the options that is saved by default.")


class RunBench(object):
    def __init__(self):
        self.home_dir = os.path.expanduser('~')
        self.root_dir = self.home_dir + "/.aibench/git/"
        parseKnown()

    def run(self):
        cmd = self._getCMD()
        getLogger().info("Running: %s", cmd)
        os.system(cmd)

    def _getUnknownArgs(self):
        unknowns = getUnknowns()
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
            '--commit_file': self.root_dir + "processed_commit",
            '--exec_dir': self.root_dir + "exec",
            '--framework': 'caffe2',
            '--local_reporter': self.root_dir + "reporter",
            '--repo': 'git',
            '--status_file': self.root_dir + "status",
            '--model_cache': self.root_dir + "model_cache",
            '--platforms': 'android',
            '--timeout': 300,
        }
        if os.path.isfile(self.root_dir + "config.txt"):
            with open(self.root_dir + "config.txt", "r") as f:
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
        with open(self.root_dir + "config.txt", "w") as f:
            json_args = json.dumps(args,
                                   indent=2, sort_keys=True)
            f.write(json_args)
        return all_args

    def _inputOneArg(self, text, key, args):
        arg = args[key] if key in args else None
        v = input(text + ' [' + str(arg) + ']: ')
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
        if getArgs().reset_options or \
                not os.path.isdir(self.root_dir) or \
                not os.path.isfile(self.root_dir + "config.txt"):
            args = self._saveDefaultArgs(new_args)
        else:
            with open(self.root_dir + "config.txt", "r") as f:
                args = json.load(f)
        for v in new_args:
            if v in args:
                del args[v]
        return args

    def _getCMD(self):
        args = self._getSavedArgs()
        unknowns = getUnknowns()
        dir_path = os.path.dirname(os.path.realpath(__file__))
        command = dir_path + "/repo_driver.py " + \
            ' '.join([self._getString(u) + ' ' +
                     (self._getString(args[u])
                      if args[u] is not None else "")
                      for u in args]) + ' ' + \
            ' '.join([self._getString(u) for u in unknowns])
        return command

    def _getString(self, s):
        s = str(s)
        if re.match("^[A-Za-z0-9_/.~-]+$", s):
            return s
        else:
            return '"' + s + '"'


if __name__ == "__main__":
    app = RunBench()
    app.run()
