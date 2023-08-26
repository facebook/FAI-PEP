from __future__ import absolute_import, division, print_function, unicode_literals

file_handles = {}


class UploadDownloadFilesBase:
    def __init__(self, args):
        self.args = args
        pass

    def upload(self, **kwargs):
        pass

    def download(self, **kwargs):
        pass


def registerUploadDownloadFiles(name, obj):
    global file_handles
    file_handles[name] = obj


def getFileHandles():
    return file_handles
