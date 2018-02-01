#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import os.path as path
import time

from platforms.platform_base import PlatformBase
from utils.arg_parse import getArgs

class AndroidPlatform(PlatformBase):
    def __init__(self, adb):
        super(AndroidPlatform, self).__init__()
        self.adb = adb
        platform = adb.shell(['getprop', 'ro.product.model'], default="").strip() + \
            '-' + \
            adb.shell(['getprop', 'dalvik.vm.isa.arm.variant'], default="").strip() + \
            '-' + \
            adb.shell(['getprop', 'ro.build.version.release'], default="").strip() + \
            '-' + \
            adb.shell(['getprop', 'ro.build.version.sdk'], default="").strip()
        self.setPlatform(platform)
        self.input_file = None
        self.android_input_dir = self.adb.dir + "/input/"
        self.android_output_dir = self.adb.dir + "/output/"

    def runBenchmark(self, info):
        self._setupPlatform(info)
        basename = path.basename(info['program'])
        program = self.adb.dir + basename
        init_net = path.basename(getArgs().init_net)
        net = path.basename(getArgs().net)
        cmd = [program,
            "--init_net", self.adb.dir + "/" + init_net,
            "--net", self.adb.dir + "/" + net,
            "--input", getArgs().input,
            "--warmup", str(getArgs().warmup),
            "--iter", str(getArgs().iter),
            ]
        if getArgs().input_file:
            assert self.input_file != None, \
                "Input file should not be None"
            input_file = ",".join(self.input_file)
            cmd.extend(["--input_file", input_file])
        if getArgs().input_dims:
            cmd.extend(["--input_dims", getArgs().input_dims])
        if getArgs().input_type:
            cmd.extend(["--input_type", getArgs().input_type])
        if getArgs().output:
            cmd.extend(["--output", getArgs().output])
            self.adb.shell(["rm", "-rf", self.android_output_dir])
            self.adb.shell(["mkdir", self.android_output_dir])
            cmd.extend(["--output_folder", self.android_output_dir])
            cmd.extend(["--text_output", "true"])
        if getArgs().run_individual:
            cmd.extend(["--run_individual", "true"])

        if getArgs().shared_libs:
            cmd = ["export", "LD_LIBRARY_PATH=" + self.adb.dir, "&&"] + cmd

        self.adb.shell(cmd, timeout=getArgs().timeout)
        log = self.adb.logcat('-d')
        self._postRun()
        return log

    def collectMetaData(self, info):
        meta = super(AndroidPlatform, self).collectMetaData(info)
        meta[self.PLATFORM] = self.platform
        return meta

    def _setupPlatform(self, info):
        try:
            self.adb.logcat("-G", "1M")
        except Exception:
            self.adb.logcat("-G", "256K")
        self.adb.logcat('-b', 'all', '-c')
        time.sleep(1)
        self.adb.push(getArgs().net)
        self.adb.push(getArgs().init_net)
        if getArgs().input_file:
            orig_input_files = self.getNameList(getArgs().input_file)
            self.input_file = [self.android_input_dir + path.basename(x)
                               for x in orig_input_files]
            for src, tgt in zip(orig_input_files, self.input_file):
                self.adb.push(src, tgt)
        if getArgs().shared_libs:
            libs = getArgs().shared_libs.split(",")
            for lib in libs:
                self.adb.push(lib)
        self.adb.push(info['program'])

    def _postRun(self):
        if getArgs().output:
            outputs = getArgs().output.strip().split(',')
            for output in outputs:
                filename = self.android_output_dir + output + ".txt"
                self.adb.pull(filename, self.output_dir)
