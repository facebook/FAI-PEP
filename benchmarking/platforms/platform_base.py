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
import abc
import json
import os
from six import string_types

from utils.custom_logger import getLogger
from utils.utilities import getFilename


class PlatformBase(object):
    def __init__(self, tempdir, tgt_dir, platform_util, args):
        self.tempdir = tempdir
        self.platform = None
        self.platform_hash = platform_util.device
        self.type = None
        self.util = platform_util
        self.tgt_dir = tgt_dir
        self.hash_platform_mapping = None
        if args.hash_platform_mapping:
            try:
                with open(args.hash_platform_mapping) as f:
                    self.hash_platform_mapping = json.load(f)
            except OSError as e:
                getLogger().info("OSError: {}".format(e))
            except ValueError as e:
                getLogger().info('Invalid json: {}'.format(e))

    def getType(self):
        return self.type

    def setPlatform(self, platform):
        self.platform = getFilename(platform)
        if self.hash_platform_mapping and \
                self.platform_hash in self.hash_platform_mapping:
            self.platform = self.hash_platform_mapping[self.platform_hash]

    def setPlatformHash(self, platform_hash):
        self.platform_hash = platform_hash
        if self.hash_platform_mapping and \
                self.platform_hash in self.hash_platform_mapping:
            self.platform = self.hash_platform_mapping[self.platform_hash]

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
    def runBenchmark(self, cmd, *args, **kwargs):
        return None

    @abc.abstractmethod
    def preprocess(self, *args, **kwargs):
        pass

    def copyFilesToPlatform(self, files, target_dir=None, copy_files=True):
        target_dir = (self.tgt_dir if target_dir is None else target_dir)
        if isinstance(files, string_types):
            target_file = os.path.join(target_dir, os.path.basename(files))
            if copy_files:
                self.util.push(files, target_file)
            return target_file
        elif isinstance(files, list):
            target_files = []
            for f in files:
                target_files.append(self.copyFilesToPlatform(f, target_dir,
                                                             copy_files))
            return target_files
        elif isinstance(files, dict):
            d = {}
            for f in files:
                d[f] = self.copyFilesToPlatform(files[f], target_dir,
                                                copy_files)
            return d
        else:
            assert False, "Cannot reach here"
        return None

    def moveFilesFromPlatform(self, files, target_dir=None):
        assert target_dir is not None, "Target directory must be specified."
        if isinstance(files, string_types):
            basename = os.path.basename(files)
            target_file = os.path.join(target_dir, basename)
            self.util.pull(files, target_file)
            self.util.deleteFile(files)
            return target_file
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

    def delFilesFromPlatform(self, files):
        if isinstance(files, string_types):
            self.util.deleteFile(files)
        elif isinstance(files, list):
            for f in files:
                self.util.deleteFile(f)
        elif isinstance(files, dict):
            for f in files:
                self.util.deleteFile(files[f])
        else:
            assert False, "Cannot reach here"

    def getOutputDir(self):
        return self.tgt_dir

    @abc.abstractmethod
    def killProgram(self, program):
        assert False, "kill program is not implemented"

    @abc.abstractmethod
    def waitForDevice(self):
        assert False, "wait for device is not implemented"

    def getPairedArguments(self, cmd):
        # do not support position arguments
        arguments = {}
        i = 0
        while i < len(cmd):
            entry = cmd[i]
            if entry[:2] == "--":
                key = entry[2:]
                value = cmd[i+1] if i < len(cmd) else "true"
                if value[:2] == "--":
                    value = "true"
                else:
                    i = i + 1
                arguments[key] = value
            elif entry != "{program}":
                getLogger.warning("Failed to get argument {}".format(entry[i]))
            i = i + 1
        return arguments
