#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import json
import os
import shlex

from platforms.platform_base import PlatformBase
from utils.arg_parse import getParser, getArgs
from utils.custom_logger import getLogger

getParser().add_argument("--ios_dir", default="/tmp",
    help="The directory in the ios device all files are pushed to.")


class IOSPlatform(PlatformBase):
    def __init__(self, tempdir, idb):
        super(IOSPlatform, self).__init__(tempdir, getArgs().ios_dir, idb)
        self.platform = None
        self.platform_hash = idb.device
        self.type = "ios"
        self.app = None

    def runCommand(self, cmd):
        return self.util.run(cmd)

    def preprocess(self, *args, **kwargs):
        if "program" not in kwargs:
            return

        self.app = kwargs["program"]
        # find out the bundle id
        assert os.path.isdir(self.app), "app is not a directory"
        bundle_id_filename = os.path.join(self.app, "bundle_id")
        assert os.path.isfile(bundle_id_filename), "bundle id file missing"
        with open(bundle_id_filename, "r") as f:
            bundle_id = f.read().strip()
            self.util.setBundleId(bundle_id)

        self.util.run(["--bundle", self.app,
                      "--uninstall", "--noninteractive"])

    def runBenchmark(self, cmd, *args, **kwargs):
        if not isinstance(cmd, list):
            cmd = shlex.split(cmd)
        assert self.util.bundle_id is not None, "Bundle id is not specified"

        arguments = {}
        i = 1
        while i < len(cmd):
            entry = cmd[i]
            if entry[:2] == "--":
                key = entry[2:]
                value = cmd[i+1]
                if value[:2] == "--":
                    value = "true"
                else:
                    i = i + 1
                arguments[key] = value
            else:
                assert False, "Only supporting arguments with double dashes"
            i = i + 1
        argument_filename = os.path.join(self.tempdir, "benchmark.json")
        arguments_json = json.dumps(arguments, indent=2, sort_keys=True)
        with open(argument_filename, "w") as f:
            f.write(arguments_json)
        tgt_argument_filename = os.path.join(self.tgt_dir, "benchmark.json")
        self.util.push(argument_filename, tgt_argument_filename)

        ios_kwargs = {}
        if "platform_args" in kwargs:
            platform_args = kwargs["platform_args"]
        if "timeout" in platform_args and platform_args["timeout"]:
            ios_kwargs["timeout"] = platform_args["timeout"]
            del platform_args["timeout"]

        run_cmd = ["--bundle", self.app, "--noninteractive"]
        # the command may fail, but the err_output is what we need
        log_screen = self.util.run(run_cmd, **ios_kwargs)
        print(log_screen)
        return log_screen
