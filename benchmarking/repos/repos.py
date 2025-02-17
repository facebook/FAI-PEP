#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


from .git import GitRepo
from .hg import HGRepo


def getRepo(repo, repo_dir):
    if repo == "git":
        return GitRepo(repo_dir)
    elif repo == "hg":
        return HGRepo(repo_dir)
    else:
        raise AssertionError("Repo not recognized")
        return None
