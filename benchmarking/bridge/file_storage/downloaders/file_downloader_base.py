##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

download_handles = {}


class FileDownloaderBase(object):
    def __init__(self):
        pass

    def download_file(self, location, path):
        pass


def registerFileDownloader(name, obj):
    global download_handles
    download_handles[name] = obj


def getDownloadHandles():
    return download_handles
