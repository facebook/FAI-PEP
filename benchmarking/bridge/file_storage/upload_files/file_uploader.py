##############################################################################
# Copyright 2022-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

upload_handles = {}


class FileUploader:
    def __init__(self, context: str = "default"):
        self.upload_handles = getUploadHandles()
        if context not in self.upload_handles:
            raise RuntimeError(f"No configuration found for {context}")
        self.uploader = self.upload_handles[context]()

    def upload_file(self, file):
        return self.uploader.upload_file(file)

    def get_uploader(self):
        return self.uploader


def registerFileUploader(name, obj):
    global upload_handles
    upload_handles[name] = obj


def getUploadHandles():
    return upload_handles
