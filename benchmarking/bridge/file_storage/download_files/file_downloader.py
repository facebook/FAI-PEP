##############################################################################
# Copyright 2022-present, Meta, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

download_handles = {}


class FileDownloader:
    def __init__(self, context: str = "default"):
        self.download_handles = getDownloadHandles()
        if context not in self.download_handles:
            raise RuntimeError(f"No configuration found for {context}")
        self.downloader = self.download_handles[context]()

    def downloadFile(self, file, blob=None):
        return self.downloader.downloadFile(file, blob=blob)

    def getDownloader(self):
        return self.downloader


def registerFileDownloader(name, obj):
    global download_handles
    download_handles[name] = obj


def getDownloadHandles():
    return download_handles
