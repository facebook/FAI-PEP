#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


from platforms.host.host_platform import HostPlatform


class WindowsPlatform(HostPlatform):
    def __init__(self, tempdir):
        super(WindowsPlatform, self).__init__(tempdir)
        self.type = "windows"
