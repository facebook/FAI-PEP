from __future__ import absolute_import, division, print_function, unicode_literals

from bridge.upload_download_files_base import registerUploadDownloadFiles
from bridge.upload_download_files_base import UploadDownloadFilesBase
from utils.custom_logger import getLogger


class UploadDownloadFilesDummy(UploadDownloadFilesBase):
    def __init__(self, args):
        super(UploadDownloadFilesDummy, self).__init__(args)

    def upload(self, **kwargs):
        getLogger().info("Uploading (dummy). Args: {}".format(kwargs))
        return kwargs['file']

    def download(self, **kwargs):
        getLogger().info("Downloading (dummy). Args: {}".format(kwargs))


registerUploadDownloadFiles("dummy", UploadDownloadFilesDummy)
