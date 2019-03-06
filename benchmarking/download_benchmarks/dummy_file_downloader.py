from __future__ import absolute_import, division, print_function, unicode_literals

from download_benchmarks.file_downloader_base import registerFileDownloader
from download_benchmarks.file_downloader_base import FileDownloaderBase

from utils.custom_logger import getLogger


class DummyFileDownloader(FileDownloaderBase):
    def __init__(self, **kwargs):
        super(DummyFileDownloader, self).__init__()
        self.logger = kwargs['logger']
        self.root_model_dir = kwargs['args'].root_model_dir
        self.everstore = None

    def download_file(self, location, path):
        path = self.root_model_dir + location
        self.logger.info("Copying {} to {}".format(location, path))

        from shutil import copyfile
        import os
        basedir = os.path.dirname(path)
        if not os.path.exists(basedir):
            os.makedirs(basedir)
        copyfile(location, path)


registerFileDownloader("dummy", DummyFileDownloader)
