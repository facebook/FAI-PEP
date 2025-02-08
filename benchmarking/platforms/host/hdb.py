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
import shutil

from platforms.platform_util_base import PlatformUtilBase
from utils.custom_logger import getLogger

COPY_THRESHOLD = 6442450944  # 6 GB


class HDB(PlatformUtilBase):
    def __init__(self, device=None, tempdir=None):
        super().__init__(device, tempdir)

    def push(self, src, tgt):
        getLogger().info(f"push {src} to {tgt}")
        if src != tgt:
            if os.path.isdir(src):
                if os.path.exists(tgt):
                    shutil.rmtree(tgt)
                shutil.copytree(src, tgt)
            else:
                if os.stat(src).st_size < COPY_THRESHOLD:
                    shutil.copyfile(src, tgt)
                    os.chmod(tgt, 0o777)
                else:
                    if not os.path.isfile(tgt):
                        getLogger().info(f"Create symlink between {src} and {tgt}")
                        os.symlink(src, tgt)

    def pull(self, src, tgt):
        getLogger().info(f"pull {src} to {tgt}")
        if src != tgt:
            shutil.copyfile(src, tgt)
            os.chmod(tgt, 0o777)

    def deleteFile(self, file, *args, **kwargs):
        getLogger().info(f"delete {file}")
        if os.path.isdir(file):
            shutil.rmtree(file)
        else:
            os.remove(file)
