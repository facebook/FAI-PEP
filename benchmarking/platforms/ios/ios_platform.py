#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


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


CHECK_COMPLETION_AT_BENCHMARK = True


class IOSPlatform(PlatformBase):
    def __init__(
        self, tempdir, platform_util, args, platform_meta, usb_controller=None
    ):
        super().__init__(
            tempdir,
            args.ios_dir,
            platform_util,
            args.hash_platform_mapping,
            args.device_name_mapping,
        )
        self.setPlatformHash(platform_util.device)
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
        self.use_xcrun = not (int(self.platform_os_version.split(".")[0]) < 17)

    def getKind(self):
        if self.platform_model and self.platform_os_version:
            return f"{self.platform_model}-{self.platform_os_version}"
        return self.platform

    def getOS(self):
        if self.platform_os_version:
            return f"iOS {self.platform_os_version}"
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
        assert len(dirs) == 1, f"Payload must contain exactly 1 app, found {len(dirs)}"
        app_name = dirs[0]
        self.app = os.path.join(app_dir, app_name)
        (base_name, _) = os.path.splitext(app_name)
        self.dsym = os.path.join(self.app, base_name + ".dSYM")
        del programs["program"]

        bundle_id, _ = processRun(["osascript", "-e", 'id of app "' + self.app + '"'])
        assert len(bundle_id) > 0, "bundle id cannot be found"
        self.util.setBundleId(bundle_id[0].strip())

        # We know this command will fail. Avoid propogating this
        # failure to the upstream
        success = getRunStatus()
        self.util.uninstallApp(self.util.bundle_id if self.use_xcrun else self.app)
        if self.use_xcrun:
            self.util.run(["install", "app", self.app, "--device", self.util.device])
        setRunStatus(success, overwrite=True)

    def postprocess(self, *args, **kwargs):
        success = getRunStatus()
        # self.util.uninstallApp(self.app)
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

        logfile = os.path.join(self.tempdir, "__app_stdout.json")
        run_cmd = (
            [
                "process",
                "launch",
                "--no-activate",
                "--terminate-existing",
                "--user",
                "mobile",
                "--verbose",
                "--json-output",
                logfile,
                "--device",
                self.util.device,
                self.util.bundle_id,
            ]
            if self.use_xcrun
            else [
                "--bundle",
                self.app,
                "--noninteractive",
                "--noinstall",
                "--unbuffered",
            ]
        )
        platform_args = {}
        if "platform_args" in kwargs:
            platform_args = kwargs["platform_args"]
            if (
                "power" in platform_args
                and platform_args["power"]
                and not self.use_xcrun
            ):
                platform_args["timeout"] = 10
                run_cmd += ["--justlaunch"]
            if platform_args.get("profiling_args", {}).get("enabled", False):
                # attempt to run with profiling, else fallback to standard run
                try:
                    profiling_types = platform_args["profiling_args"]["types"]
                    options = platform_args["profiling_args"]["options"]
                    args = " ".join(["--" + x + " " + arguments[x] for x in arguments])
                    xctrace = getProfilerByUsage(
                        "ios",
                        None,
                        platform=self,
                        model_name=platform_args.get("model_name", None),
                        args=args,
                        types=profiling_types,
                        options=options,
                    )
                    if xctrace:
                        f = xctrace.start()
                        output, meta = f.result()
                        if not output or not meta:
                            raise RuntimeError(
                                "No data returned from XCTrace profiler."
                            )
                        return output, meta
                except Exception:
                    getLogger().exception(
                        f"An error occurred when running XCTrace profiler on device {self.platform} {self.platform_hash}."
                    )
        # meta is used to store any data about the benchmark run
        # that is not the output of the command
        meta = {}

        if arguments:
            if not self.use_xcrun:
                run_cmd += [
                    "--args",
                    " ".join(["--" + x + " " + arguments[x] for x in arguments]),
                ]
            else:
                for x in arguments:
                    run_cmd += [f"--{x}"]
                    run_cmd += [f"{arguments[x]}"]
        # the command may fail, but the err_output is what we need
        log_screen = self.util.run(run_cmd, **platform_args)
        if os.path.isfile(logfile):
            with open(logfile) as f:
                getLogger().info(f.read())

        if self.use_xcrun:
            # Since XCRun doesn't provide logs, we generate a file with the logs on the device (for ExecuTorch benchmark) at /tmp/BENCH_LOG. Once the benchmark completes, /tmp/BENCH_DONE will be created.
            # The xcrun command to detect fiels takes a while. 15 seconds should be enough for the commandto complete.
            timeout = kwargs.get("platform_args", {}).get("timeout", 1200)
            check_completion_by_xcrun = CHECK_COMPLETION_AT_BENCHMARK
            completion_file = "tmp/BENCH_DONE"
            getLogger().info(
                f"Benchmark timeout is {timeout} seconds. (iOS aibench cannot reliably detect benchmark completion), "
                + f"using check_completion_by_xcrun={check_completion_by_xcrun}, can be turned off at benchmarking/ios/ios_platform.py"
            )
            log_checker_wait = 15
            time_counter = 0
            while time_counter <= timeout:
                time.sleep(log_checker_wait)
                time_counter += log_checker_wait
                getLogger().info(
                    f"Benchmark counter waiting for app run complete (heartbeat every {log_checker_wait} seconds)."
                )
                if check_completion_by_xcrun:
                    files = self.util.listFiles()
                    if any(completion_file in file_entry for file_entry in files):
                        break

            if check_completion_by_xcrun:
                files = self.util.listFiles()
                if not any(completion_file in file_entry for file_entry in files):
                    getLogger().info(
                        f"Benchmark did not complete within the timeout period ({timeout} seconds)."
                    )

            self.util.pull("/tmp/BENCH_LOG", logfile)

            if os.path.isfile(logfile):
                logfile_reader = open(logfile)
                logfile_contents = logfile_reader.read()
                getLogger().info("\n\t[ ======= Benchmark Logs ======= ]")
                getLogger().info(logfile_contents)
                getLogger().info("\t[ ===== End Benchmark Logs ===== ]\n")
                log_screen = logfile_contents
                logfile_reader.close()

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
