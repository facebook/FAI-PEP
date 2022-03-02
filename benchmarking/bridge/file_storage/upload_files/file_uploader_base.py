from __future__ import absolute_import, division, print_function, unicode_literals

upload_handles = {}


class FileUploaderBase(object):
    def __init__(self):
        pass

    def upload_file(self, location, context, **kwargs):
        pass


def registerFileUploader(name, obj):
    global upload_handles
    upload_handles[name] = obj


def getUploadHandles():
    return upload_handles
