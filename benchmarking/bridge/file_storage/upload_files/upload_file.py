##############################################################################
# Copyright 2022-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


from bridge.file_storage.upload_files.file_uploader_base import getUploadHandles


class UploadFile:
    def __init__(self):
        self.upload_handles = getUploadHandles()
        self.uploaders = {}

    def upload_file(self, file, context: str, **kwargs):
        if context not in self.upload_handles:
            raise RuntimeError(f"No configuration found for {context}")
        uploader = self.uploaders.get(context, self.upload_handles[context]())
        return uploader.upload_file(file, context=context, **kwargs)
