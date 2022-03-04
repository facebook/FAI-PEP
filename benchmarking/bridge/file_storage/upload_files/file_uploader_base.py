##############################################################################
# Copyright 2022-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

upload_handles = {}


class FileUploaderBase:
    def __init__(self):
        pass

    def upload_file(self, location, context, **kwargs):
        pass


def registerFileUploader(name, obj):
    global upload_handles
    upload_handles[name] = obj


def getUploadHandles():
    return upload_handles
