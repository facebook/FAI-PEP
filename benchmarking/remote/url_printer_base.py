# pyre-unsafe
from __future__ import absolute_import, division, print_function, unicode_literals

result_url_handles = {}


class URLPrinterBase:
    def __init__(self):
        pass

    def printURL(self, dataset, user_identifier, benchmarks):
        pass


def registerResultURL(name, obj):
    global result_url_handles
    result_url_handles[name] = obj


def getResultURLHandles():
    return result_url_handles
