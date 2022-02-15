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

import os
import shutil
import sys

from platforms.platform_util_base import PlatformUtilBase
from utils.custom_logger import getLogger


class IDB(PlatformUtilBase):
    def __init__(self, device=None, tempdir=None):
        super(IDB, self).__init__(device, tempdir)
        self.bundle_id = None
        if self.tempdir is not None:
            self.cached_tree = os.path.join(self.tempdir, "tree")
            if not os.path.isdir(self.cached_tree):
                os.mkdir(self.cached_tree)

    def setBundleId(self, bundle_id):
        self.bundle_id = bundle_id

    def run(self, *args, **kwargs):
        idb = ["ios-deploy"]
        if self.device:
            idb.extend(["--id", self.device])
        if self.bundle_id:
            idb.extend(["--bundle_id", self.bundle_id])
        return super(IDB, self).run(idb, *args, **kwargs)

    def push(self, src, tgt):
        # only push files, not directories, as apps are directories
        if os.path.isdir(src):
            getLogger().info("Skip pushing directory {}".format(src))
            return
        return self.run("--upload", src, "--to", tgt)

    def pull(self, src, tgt):
        # ios-deploy will dump all files from the app to the directory,
        # so we only dump it once and save the result.
        # it is better to remove all uncessary files before we dump the
        # result
        assert self.cached_tree is not None, "cached_tree is None."
        src_filename = os.path.join(self.cached_tree, src)
        if not os.path.isfile(src_filename):
            self.run("--download", "--to", self.cached_tree)
        assert os.path.isfile(src_filename), "File {} doesn't exist in app".format(
            src_filename
        )
        shutil.copyfile(src_filename, tgt)

    def reboot(self):
        # use idevicediagnostics to reboot device if exists
        try:
            super(IDB, self).run("idevicepair", "-u", self.device, "pair")
            super(IDB, self).run("idevicediagnostics", "-u", self.device, "restart")
            return True
        except Exception:
            getLogger().critical(
                f"Rebooting failure for device {self.device}.",
                exc_info=True,
            )
            return False

    def deleteFile(self, file):
        # need to make sure the file exists
        # return self.run("--rm", file)
        # no need to delete file since files are added to a bundle
        # and the app is installed in every benchmark
        pass

    def batteryLevel(self):
        try:
            response = self.run("--get_battery_level")
            level = int(response[-1].lstrip("BatteryCurrentCapacity:"))

            getLogger().info("Result {}".format(level))
            return level
        except Exception:
            getLogger().critical(
                f"Could not read battery level for device {self.device}.",
                exc_info=True,
            )
            return -1
