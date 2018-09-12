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
from utils.subprocess_with_logger import processRun

getParser().add_argument("--ios_dir", default="/tmp",
    help="The directory in the ios device all files are pushed to.")


class IOSPlatform(PlatformBase):
    def __init__(self, tempdir, idb):
        super(IOSPlatform, self).__init__(tempdir, getArgs().ios_dir, idb)
        self.setPlatformHash(idb.device)
        self.type = "ios"
        self.app = None

    def runCommand(self, cmd):
        return self.util.run(cmd)

    def preprocess(self, *args, **kwargs):
        assert "programs" in kwargs, "Must have programs specified"

        programs = kwargs["programs"]

        # find the first zipped app file
        assert "program" in programs, "program is not specified"
        program = programs["program"]
        assert program.endswith(".ipa"), \
            "IOS program must be an ipa file"

        processRun(["unzip", "-o", "-d", self.tempdir, program])
        # get the app name
        app_dir = os.path.join(self.tempdir, "Payload")
        dirs = [f for f in os.listdir(app_dir)
                if os.path.isdir(os.path.join(app_dir, f))]
        assert len(dirs) == 1, "Only one app in the Payload directory"
        app_name = dirs[0]
        self.app = os.path.join(app_dir, app_name)
        del programs["program"]

        bundle_id, _ = processRun(["osascript", "-e",
                                   "id of app \"" + self.app + "\""])

        self.util.setBundleId(bundle_id.strip())

        self.util.run(["--bundle", self.app,
                      "--uninstall", "--noninteractive"])

    def runBenchmark(self, cmd, *args, **kwargs):
        if not isinstance(cmd, list):
            cmd = shlex.split(cmd)
        assert self.util.bundle_id is not None, "Bundle id is not specified"

        arguments = {}
        i = 0
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

        run_cmd = ["--bundle", self.app, "--noninteractive", "--noinstall"]
        # the command may fail, but the err_output is what we need
        log_screen = self.util.run(run_cmd, **ios_kwargs)
        return log_screen
