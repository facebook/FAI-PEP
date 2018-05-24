#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from .git import GitRepo
from .hg import HGRepo
from utils.arg_parse import getArgs


def getRepo():
    repo = getArgs().repo
    repo_dir = getArgs().repo_dir
    if repo == 'git':
        return GitRepo(repo_dir)
    elif repo == 'hg':
        return HGRepo(repo_dir)
    else:
        assert False, "Repo not recognized"
        return None
