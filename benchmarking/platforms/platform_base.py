#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import abc
from utils.utilities import getFilename


class PlatformBase(object):
    # Class constant, need to change observer_reporter_print.cc
    # if the names are changed
    IDENTIFIER = 'Caffe2Observer '
    NET_NAME = 'Net Name'
    NET_DELAY = 'NET_DELAY'
    DELAYS_START = 'Delay Start'
    DELAYS_END = 'Delay End'
    DATA = 'data'
    META = 'meta'
    PLATFORM = 'platform'
    COMMIT = 'commit'

    def __init__(self):
        self.tempdir = None
        self.platform = None
        self.platform_hash = None

    def setPlatform(self, platform):
        self.platform = getFilename(platform)

    def getName(self):
        return self.platform

    def getMangledName(self):
        name = self.platform
        if self.platform_hash:
            name = name + " ({})".format(self.platform_hash)
        return name

    def rebootDevice(self):
        pass

    @abc.abstractmethod
    def runBenchmark(self, info):
        return None

    @abc.abstractmethod
    def copyFilesToPlatform(self, files, target_dir=None):
        return files

    @abc.abstractmethod
    def moveFilesFromPlatform(self, files, target_dir=None):
        return files

    @abc.abstractmethod
    def delFilesFromPlatform(self, files):
        pass

    @abc.abstractmethod
    def getOutputDir(self):
        pass
