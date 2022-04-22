##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import os

import requests
from bridge.file_storage.downloaders.file_downloader_base import FileDownloaderBase
from bridge.file_storage.downloaders.file_downloader_base import registerFileDownloader
from utils.custom_logger import getLogger


class DjangoFileDownloader(FileDownloaderBase):
    def __init__(self, **kwargs):
        super(DjangoFileDownloader, self).__init__()
        self.root_model_dir = kwargs["args"].root_model_dir

    def download_file(self, location, path):
        getLogger().info("Downloading from {} to {}".format(location, path))
        basedir = os.path.dirname(path)
        if not os.path.exists(basedir):
            os.makedirs(basedir)

        r = requests.get(location)
        if r.status_code == 200:
            with open(path, "wb") as f:
                f.write(r.content)


registerFileDownloader("http", DjangoFileDownloader)
