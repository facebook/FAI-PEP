#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import os

from platforms.platform_base import PlatformBase
from utils.arg_parse import getArgs


class AndroidPlatform(PlatformBase):
    def __init__(self, tempdir, adb):
        super(AndroidPlatform, self).__init__()
        self.adb = adb
        platform = adb.shell(
            ['getprop', 'ro.product.model'], default="").strip() + \
            '-' + \
            adb.shell(
            ['getprop', 'dalvik.vm.isa.arm.variant'], default="").strip() + \
            '-' + \
            adb.shell(
            ['getprop', 'ro.build.version.release'], default="").strip() + \
            '-' + \
            adb.shell(['getprop', 'ro.build.version.sdk'], default="").strip()
        self.setPlatform(platform)
        self.tempdir = tempdir + "/" + self.platform
        os.makedirs(self.tempdir, 0o777, True)
        self.platform_hash = adb.device
        self.setLogCatSize()

    def setLogCatSize(self):
        repeat = True
        size = 131072
        while (repeat and size > 256):
            try:
                repeat = False
                self.adb.logcat("-G", str(size) + "K")
            except Exception:
                repeat = True
                size = size / 2

    def runBenchmark(self, cmd):
        self.adb.logcat('-b', 'all', '-c')
        self.adb.shell(cmd, timeout=getArgs().timeout)
        log = self.adb.logcat('-d')
        return log

    def collectMetaData(self, info):
        meta = super(AndroidPlatform, self).collectMetaData(info)
        meta['platform_hash'] = self.platform_hash
        return meta

    def copyFilesToPlatform(self, files, target_dir=None):
        target_dir = (self.adb.dir if target_dir is None else target_dir) + "/"
        if isinstance(files, str):
            target_file = target_dir + os.path.basename(files)
            self.adb.push(files, target_file)
            return target_file
        elif isinstance(files, list):
            target_files = []
            for f in files:
                target_files.append(self.copyFilesToPlatform(f, target_dir))
            return target_files
        elif isinstance(files, dict):
            d = {}
            for f in files:
                d[f] = self.copyFilesToPlatform(files[f], target_dir)
            return d
        else:
            assert False, "Cannot reach here"
        return None

    def moveFilesFromPlatform(self, files, target_dir):
        assert target_dir is not None, "Target directory must be specified."
        if isinstance(files, str):
            return self._moveOneFileFromPlatform(files, target_dir)
        elif isinstance(files, list):
            output_files = []
            for f in files:
                output_files.append(self.moveFilesFromPlatform(f, target_dir))
            return output_files
        elif isinstance(files, dict):
            output_files = {}
            for f in files:
                output_file = self.moveFilesFromPlatform(files[f],
                                                         target_dir)
                output_files[f] = output_file
            return output_files
        else:
            assert False, "Cannot reach here"
        return None

    def _moveOneFileFromPlatform(self, f, target_dir):
        basename = os.path.basename(f)
        android_file = self.adb.dir + basename
        output_file = target_dir + basename
        self.adb.pull(android_file, output_file)
        self.adb.shell(["rm", "-f", android_file])
        return output_file

    def delFilesFromPlatform(self, files):
        if isinstance(files, str):
            self.adb.deleteFile(files)
        elif isinstance(files, list):
            for f in files:
                self.adb.deleteFile(f)
        elif isinstance(files, dict):
            for f in files:
                self.adb.deleteFile(files[f])
        else:
            assert False, "Cannot reach here"


    def getOutputDir(self):
        return self.adb.dir
