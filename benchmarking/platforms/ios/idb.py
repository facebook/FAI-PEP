#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import os

from platforms.platform_util_base import PlatformUtilBase
from utils.custom_logger import getLogger


class IDB(PlatformUtilBase):
    def __init__(self, device=None):
        super(IDB, self).__init__(device)
        self.bundle_id = None

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
        return self.run("--download", src, "--to", tgt)

    def reboot(self):
        # No reboot functionality
        pass

    def deleteFile(self, file):
        # need to make sure the file exists
        # return self.run("--rm", file)
        # no need to delete file since files are added to a bundle
        # and the app is installed in every benchmark
        pass
