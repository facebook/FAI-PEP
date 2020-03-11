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
import datetime
import platform
import os
import re
import sys
import shlex
import shutil
import socket
import time

from platforms.host.hdb import HDB
from platforms.platform_base import PlatformBase
from utils.custom_logger import getLogger
from utils.subprocess_with_logger import processRun, processWait
from utils.utilities import getRunTimeout
from profilers.profilers import getProfilerByUsage


class HostPlatform(PlatformBase):
    def __init__(self, tempdir, args):
        platform_hash = str(socket.gethostname())
        if args.platform_sig is not None:
            platform_name = str(args.platform_sig)
        else:
            platform_name = platform.platform() + "-" + \
                self._getProcessorName()
        self.tempdir = os.path.join(tempdir, platform_hash)
        hdb = HDB(platform_hash, tempdir)
        super(HostPlatform, self).__init__(self.tempdir, self.tempdir, hdb,
                                           args.hash_platform_mapping)

        # reset the platform and platform hash
        self.setPlatform(platform_name)
        self.setPlatformHash(platform_hash)
        if os.path.exists(self.tempdir):
            shutil.rmtree(self.tempdir)
        os.makedirs(self.tempdir, 0o777)
        self.type = "host"

    def runBenchmark(self, cmd, *args, **kwargs):
        if not isinstance(cmd, list):
            cmd = shlex.split(cmd)
        platform_args = {}
        env = os.environ
        if "platform_args" in kwargs:
            platform_args = kwargs["platform_args"]
            if "env" in platform_args:
                customized_env = platform_args["env"]
                for k in customized_env:
                    env[k] = str(customized_env[k])
                platform_args["env"] = env
        # enable async if profiling was requested
        runAsync = False
        if "enable_profiling" in platform_args:
            runAsync = platform_args["enable_profiling"]
            del platform_args["enable_profiling"]
        platform_args["async"] = runAsync
        profiler_args = {}
        if "profiler_args" in platform_args:
            profiler_args = platform_args["profiler_args"]
            del platform_args["profiler_args"]

        # meta is used to store any data about the benchmark run
        # that is not the output of the command
        meta = {}

        if not runAsync:
            output, _ = processRun(cmd, **platform_args)
            if not output and getRunTimeout():
                getLogger().info("Terminating...")
                sys.exit(0)
            return output, meta
        from_time = datetime.datetime.now()
        procAndTimeout, err = processRun(cmd, **platform_args)
        if err:
            return [], meta

        ps, _ = procAndTimeout

        profiler = getProfilerByUsage("server", os.getpid())

        if profiler:
            profilerFuture = profiler.start(**profiler_args)

        output, _ = processWait(procAndTimeout, **platform_args)
        # Sleep the host to make sure there is no other process running
        # if the duration of process is short
        to_time = datetime.datetime.now()
        duration = (to_time - from_time).total_seconds()
        min_duration = 5
        if duration < min_duration * 60:
            diff = min_duration * 60 - duration
            getLogger().info(
                "Sleep for {} - {} = {} seconds".format(
                    min_duration * 60, duration, diff)
            )
            time.sleep(diff)

        if profiler:
            profilerRunId = profiler.getId(profilerFuture)
            meta["profiler_run_id"] = profilerRunId

        return output, meta

    def _getProcessorName(self):
        if platform.system() == "Windows":
            return platform.processor()
        elif platform.system() == "Darwin":
            processor_info, _ = processRun(
                ["sysctl", "-n", "machdep.cpu.brand_string"])
            if len(processor_info) > 0:
                return processor_info[0].rstrip()
        elif platform.system() == "Linux":
            processor_info, _ = processRun(["cat", "/proc/cpuinfo"])
            if processor_info:
                for line in processor_info:
                    if "model name" in line:
                        return re.sub(".*model name.*:", "", line, 1)
        return ""

    def getOutputDir(self):
        out_dir = os.path.join(self.tempdir, "output")
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir, 0o777)
        return out_dir
