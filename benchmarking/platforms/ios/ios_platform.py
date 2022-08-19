#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import re
import shlex
import time

from platforms.platform_base import PlatformBase
from profilers.profilers import getProfilerByUsage
from utils.custom_logger import getLogger
from utils.subprocess_with_logger import processRun
from utils.utilities import getRunStatus, setRunStatus


class IOSPlatform(PlatformBase):
    def __init__(self, tempdir, idb, args, platform_meta, usb_controller=None):
        super(IOSPlatform, self).__init__(
            tempdir,
            args.ios_dir,
            idb,
            args.hash_platform_mapping,
            args.device_name_mapping,
        )
        self.setPlatformHash(idb.device)
        if self.platform:
            self.platform_model = (
                re.findall(r"(.*)-[0-9.]+", self.platform) or [self.platform]
            )[0]
        else:
            self.platform_model = platform_meta.get("model")
        self.platform_os_version = platform_meta.get("os_version")
        self.platform_abi = platform_meta.get("abi")
        self.usb_controller = usb_controller
        self.type = "ios"
        self.app = None

    def getKind(self):
        if self.platform_model and self.platform_os_version:
            return "{}-{}".format(self.platform_model, self.platform_os_version)
        return self.platform

    def getOS(self):
        if self.platform_os_version:
            return "iOS {}".format(self.platform_os_version)
        return "iOS"

    def preprocess(self, *args, **kwargs):
        assert "programs" in kwargs, "Must have programs specified"

        programs = kwargs["programs"]

        # find the first zipped app file
        assert "program" in programs, "program is not specified"
        program = programs["program"]
        assert program.endswith(".ipa"), "IOS program must be an ipa file"

        processRun(["unzip", "-o", "-d", self.tempdir, program])
        # get the app name
        app_dir = os.path.join(self.tempdir, "Payload")
        dirs = [
            f for f in os.listdir(app_dir) if os.path.isdir(os.path.join(app_dir, f))
        ]
        assert len(dirs) == 1, "Only one app in the Payload directory"
        app_name = dirs[0]
        self.app = os.path.join(app_dir, app_name)
        del programs["program"]

        bundle_id, _ = processRun(["osascript", "-e", 'id of app "' + self.app + '"'])
        assert len(bundle_id) > 0, "bundle id cannot be found"
        self.util.setBundleId(bundle_id[0].strip())

        # We know this command will fail. Avoid propogating this
        # failure to the upstream
        success = getRunStatus()
        self.util.run(["--bundle", self.app, "--uninstall", "--justlaunch"])
        setRunStatus(success, overwrite=True)

    def postprocess(self, *args, **kwargs):
        success = getRunStatus()
        self.util.run(["--bundle", self.app, "--uninstall_only"])
        setRunStatus(success, overwrite=True)

    def runBenchmark(self, cmd, *args, **kwargs):
        if not isinstance(cmd, list):
            cmd = shlex.split(cmd)
        assert self.util.bundle_id is not None, "Bundle id is not specified"

        arguments = self.getPairedArguments(cmd)
        argument_filename = os.path.join(self.tempdir, "benchmark.json")
        arguments_json = json.dumps(arguments, indent=2, sort_keys=True)
        with open(argument_filename, "w") as f:
            f.write(arguments_json)
        tgt_argument_filename = os.path.join(self.tgt_dir, "benchmark.json")
        self.util.push(argument_filename, tgt_argument_filename)

        run_cmd = [
            "--bundle",
            self.app,
            "--noninteractive",
            "--noinstall",
            "--unbuffered",
        ]
        platform_args = {}
        if "platform_args" in kwargs:
            platform_args = kwargs["platform_args"]
            if "power" in platform_args and platform_args["power"]:
                platform_args["timeout"] = 10
                run_cmd += ["--justlaunch"]
        if platform_args.get("enable_profiling", False):
            # attempt to run with profiling, else fallback to standard run
            try:
                args = " ".join(["--" + x + " " + arguments[x] for x in arguments])
                xctrace = getProfilerByUsage(
                    "ios",
                    None,
                    platform=self,
                    model_name=platform_args.get("model_name", None),
                    args=args,
                )
                if xctrace:
                    f = xctrace.start()
                    output, meta = f.result()
                    if not output or not meta:
                        raise RuntimeError("No data returned from XCTrace profiler.")
                    return output, meta
            except Exception:
                getLogger().critical(
                    f"An error occurred when running XCTrace profiler on device {self.platform} {self.platform_hash}.",
                    exc_info=True,
                )
        # meta is used to store any data about the benchmark run
        # that is not the output of the command
        meta = {}

        if arguments:
            run_cmd += [
                "--args",
                " ".join(["--" + x + " " + arguments[x] for x in arguments]),
            ]
        # the command may fail, but the err_output is what we need
        log_screen = self.util.run(run_cmd, **platform_args)
        return log_screen, meta

    def rebootDevice(self):
        success = self.util.reboot()
        if success:
            time.sleep(180)

    def killProgram(self, program):
        # TODO Implement or find workaround for hardware power measurement
        pass

    def currentPower(self):
        result = self.util.batteryLevel()
        return result

    @property
    def powerInfo(self):
        return {"unit": "percentage", "metric": "batteryLevel"}
