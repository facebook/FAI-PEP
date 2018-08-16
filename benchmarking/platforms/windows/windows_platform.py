#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import platform
import os
import random
import re
import shlex
import shutil
import socket
import subprocess

from platforms.host.host_platform import HostPlatform
from six import string_types
from utils.custom_logger import getLogger
from utils.arg_parse import getArgs
from utils.subprocess_with_logger import processRun


class WindowsPlatform(HostPlatform):
    def __init__(self, tempdir):
        super(WindowsPlatform, self).__init__(tempdir)
        self.type = "windows"
