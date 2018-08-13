#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import copy
import datetime
import os
import sys


def getDirectory(commit_hash, commit_time):
    dt = datetime.datetime.utcfromtimestamp(commit_time)
    directory = os.path.join(str(dt.year), str(dt.month), str(dt.day),
        commit_hash)
    return directory


def getCommand(command):
    exe = command[0]
    args = [x if x.isdigit() else "'" + x + "'" for x in command[1:]]
    cmd = exe + ' ' + ' '.join(args)
    return cmd


def getFilename(name):
    filename = name.replace(' ', '-').replace('/', '-').replace('\', '-')
    return "".join([c for c in filename
                    if c.isalpha() or c.isdigit() or
                    c == '_' or c == '.' or c == '-']).rstrip()


def getPythonInterpreter():
    return sys.executable


def deepMerge(tgt, src):
    if isinstance(src, list):
        # only handle simple lists
        for item in src:
            if item not in tgt:
                tgt.append(copy.deepcopy(item))
    elif isinstance(src, dict):
        for name in src:
            m = src[name]
            if name not in tgt:
                tgt[name] = copy.deepcopy(m)
            else:
                deepMerge(tgt[name], m)
    else:
        # tgt has already specified a value
        # src does not override tgt
        return
