from __future__ import absolute_import, division, print_function, unicode_literals

from download_benchmarks.file_downloader_base import getDownloadHandles

import download_benchmarks.django_file_downloader


class DownloadFile(object):
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
                self.downloaders[d_key] =\
                    self.download_handles[d_key](logger=self.logger,
                                                 args=self.args)

            self.downloaders[d_key].download_file(location, path)
