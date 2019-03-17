from __future__ import absolute_import, division, print_function, unicode_literals

from bridge.upload_download_files_base import getFileHandles

import bridge.upload_download_files_django


class UploadDownloadFiles(object):
    def __init__(self, args):
        self.args = args
        self.file_handles = getFileHandles()

        file_storage = self.args.file_storage
        self.obj = None
        if file_storage in self.file_handles:
            self.obj = self.file_handles[file_storage](self.args)

    def upload(self, **kwargs):
        res = ''
        if self.obj is not None:
            res = self.obj.upload(**kwargs)
        return res

    def download(self, **kwargs):
        if self.obj is not None:
            self.obj.download(**kwargs)
