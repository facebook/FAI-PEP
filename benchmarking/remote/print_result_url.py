from __future__ import absolute_import, division, print_function, unicode_literals

import remote.django_url_printer
from remote.url_printer_base import getResultURLHandles


class PrintResultURL:
    def __init__(self, args):
        self.args = args
        self.result_url_handles = getResultURLHandles()

        result_db = self.args.result_db
        self.obj = None
        if result_db in self.result_url_handles:
            self.obj = self.result_url_handles[result_db](self.args)

    def printURL(self, dataset=None, user_identifier=None, benchmarks=None):
        if self.obj is not None:
            self.obj.printURL(dataset, user_identifier, benchmarks)
