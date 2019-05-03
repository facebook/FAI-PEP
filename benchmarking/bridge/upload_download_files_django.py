from __future__ import absolute_import, division, print_function, unicode_literals

import os
import requests

from bridge.upload_download_files_base import registerUploadDownloadFiles
from bridge.upload_download_files_base import UploadDownloadFilesBase
from utils.custom_logger import getLogger
from utils.utilities import requestsJson


class UploadDownloadFilesDjango(UploadDownloadFilesBase):
    def __init__(self, args):
        super(UploadDownloadFilesDjango, self).__init__(args)
        self.server_addr = self.args.server_addr

    def upload(self, **kwargs):
        path = kwargs['file']
        if self.server_addr:
            storage_addr = self.server_addr + "/upload/"
            getLogger().info("Uploading {} to {}".format(path, storage_addr))
            filename = os.path.basename(path)

            with open(path, "rb") as f:
                result_json = requestsJson(storage_addr,
                                           files={'file': (filename, f.read())})

        url = ''
        if result_json['status'] == 'success':
            url = self.server_addr + "/" + result_json['path']
        getLogger().info("File has been uploaded to {}".format(url))
        return url

    def download(self, **kwargs):
        # Download is handled in django_file_downloader
        pass


registerUploadDownloadFiles("django", UploadDownloadFilesDjango)
