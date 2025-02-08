#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


import os

from platforms.host.host_platform import HostPlatform


class WindowsPlatform(HostPlatform):
    def __init__(self, tempdir):
        super().__init__(tempdir)
        self.type = "windows"

    def getOS(self):
        ver = os.sys.getwindowsversion()
        return f"Windows {ver.major}.{ver.minor} build {ver.build}"
