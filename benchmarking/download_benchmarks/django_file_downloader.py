# pyre-unsafe

import os

import requests
from download_benchmarks.file_downloader_base import (
    FileDownloaderBase,
    registerFileDownloader,
)
from utils.custom_logger import getLogger


class DjangoFileDownloader(FileDownloaderBase):
    def __init__(self, **kwargs):
        super().__init__()
        self.root_model_dir = kwargs["args"].root_model_dir

    def download_file(self, location, path):
        # Assume the file is the same
        if os.path.exists(location):
            return
        getLogger().info(f"Downloading from {location} to {path}")
        basedir = os.path.dirname(path)
        if not os.path.exists(basedir):
            os.makedirs(basedir)

        r = requests.get(location)
        if r.status_code == 200:
            with open(path, "wb") as f:
                f.truncate(0)
                f.write(r.content)


registerFileDownloader("http", DjangoFileDownloader)
