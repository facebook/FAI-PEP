##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

file_handles = {}


class UploadDownloadFilesBase(object):
    def __init__(self, args):
        self.args = args
        pass

    def upload(self, **kwargs):
        pass

    def download(self, **kwargs):
        pass


def registerUploadDownloadFiles(name, obj):
    global file_handles
    file_handles[name] = obj


def getFileHandles():
    return file_handles
