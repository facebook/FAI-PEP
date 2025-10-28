# pyre-unsafe

import download_benchmarks.django_file_downloader  # noqa: F401 - registers DjangoFileDownloader via side effect
from download_benchmarks.file_downloader_base import getDownloadHandles


class DownloadFile:
    def __init__(self, dirs, logger, args):
        self.args = args
        self.dirs = dirs
        self.logger = logger

        self.download_handles = getDownloadHandles()
        self.downloaders = {}

    def download_file(self, location, path):
        d_key = self.dirs[0]
        if d_key in self.download_handles:
            if d_key not in self.downloaders:
                self.downloaders[d_key] = self.download_handles[d_key](
                    logger=self.logger, args=self.args
                )

            self.downloaders[d_key].download_file(location, path)
