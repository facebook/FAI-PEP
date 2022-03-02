from __future__ import absolute_import, division, print_function, unicode_literals

from bridge.file_storage.upload_files.file_uploader_base import getUploadHandles


class UploadFile(object):
    def __init__(self):
        self.upload_handles = getUploadHandles()
        self.uploaders = {}

    def upload_file(self, file, context: str, **kwargs):
        if context not in self.upload_handles:
            raise RuntimeError(f"No configuration found for {context}")
        uploader = self.uploaders.get(context, self.upload_handles[context]())
        return uploader.upload_file(file, context=context, **kwargs)
