#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from utils.subprocess_with_logger import processRun
import os.path as path
from utils.custom_logger import getLogger
from utils.arg_parse import getParser, getArgs

getParser().add_argument("--android_dir", default="/data/local/tmp/",
    help="The directory in the android device all files are pushed to.")

class ADB(object):
    def __init__(self, device=None):
        self.device = device
        self.dir = getArgs().android_dir

    def run(self, cmd, *args, **kwargs):
        adb = ["adb"]
        if self.device:
            adb.append("-s")
            adb.append(self.device)
        adb.append(cmd)
        for item in args:
            if isinstance(item, list):
                adb.extend(item)
            else:
                adb.append(item)
        if not 'timeout' in kwargs:
            kwargs['timeout'] = 10
        return processRun(adb, **kwargs)

    def push(self, src, tgt = None):
        target = tgt if tgt != None else self.dir + path.basename(src)
        return self.run("push", src, target)

    def pull(self, src, tgt):
        return self.run("pull", src, tgt)

    def logcat(self, *args):
        return self.run("logcat", *args)

    def shell(self, cmd, **kwargs):
        return self.run("shell", cmd, **kwargs)
