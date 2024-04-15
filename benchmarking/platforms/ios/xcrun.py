#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import shlex

from platforms.ios.idb import IDB
from utils.custom_logger import getLogger


class xcrun(IDB):
    def __init__(self, device=None, tempdir=None):
        super(xcrun, self).__init__(device, tempdir)
        self.bundle_id = None
        if self.tempdir is not None:
            self.cached_tree = os.path.join(self.tempdir, "tree")
            if not os.path.isdir(self.cached_tree):
                os.mkdir(self.cached_tree)

    def setBundleId(self, bundle_id):
        self.bundle_id = bundle_id

    def run(self, *args, **kwargs):
        cmd = [
            "xcrun",
            "devicectl",
            "device",
        ]

        return super(IDB, self).run(cmd, *args, **kwargs)

    def push(self, src, tgt):
        # only push files, not directories, as apps are directories
        if os.path.isdir(src):
            getLogger().info("Skip pushing directory {}".format(src))
            return
        cmd = [
            "copy",
            "to",
            "--source",
            src,
            "--destination",
            tgt,
        ]
        if self.device:
            cmd.extend(["--device", self.device])
        if self.bundle_id:
            cmd.extend(
                [
                    "--domain-type",
                    "appDataContainer",
                    "--domain-identifier",
                    self.bundle_id,
                    "--user",
                    "mobile",
                ]
            )
        return self.run(cmd)

    def pull(self, src, tgt):
        if not os.path.isdir(os.path.dirname(tgt)):
            os.mkdir(tgt)
        cmd = [
            "copy",
            "from",
            "--source",
            shlex.quote(src),
            "--destination",
            shlex.quote(tgt),
            "--domain-type",
            "appDataContainer",
            "--domain-identifier",
            self.bundle_id,
            "--user",
            "mobile",
            "--device",
            self.device,
        ]
        return self.run(cmd)

    def reboot(self):
        cmd = ["reboot", "--device", self.device]
        return self.run(cmd)

    def listFiles(self):
        list_files_cmd = [
            "info",
            "files",
            "--domain-type",
            "appDataContainer",
            "--domain-identifier",
            self.bundle_id,
            "--username",
            "mobile",
            "--device",
            self.device,
        ]

        rows = self.run(list_files_cmd)
        # All of the files are listed below a line of dashes ----
        line_row_idx = 0
        for i in range(0, len(rows)):
            if rows[i].startswith("----"):
                line_row_idx = i
                break

        return rows[line_row_idx + 1 :]

    def deleteFile(self, file, **kwargs):
        # files will be deleted when the app is uninstalled
        pass

    def batteryLevel(self):
        # We can still use idb for device information like this
        return super().batteryLevel()

    def uninstallApp(self, bundle):
        return self.run(["uninstall", "app", bundle, "--device", self.device])
