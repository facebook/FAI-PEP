from __future__ import absolute_import, division, print_function, unicode_literals

from remote.url_printer_base import URLPrinterBase
from remote.url_printer_base import registerResultURL

DJANGO_SUB_URL = "benchmark/visualize"


class DjangoURLPrinter(URLPrinterBase):
    def __init__(self, args):
        self.args = args
        self.db_url = self.args.server_addr + DJANGO_SUB_URL

    def getDjangoParams(self, user_identifier):
        params = {
            'columns': [
                "identifier",
                "metric",
                "net_name",
                "p10",
                "p50",
                "p90",
                "platform",
                "time",
                "type",
                "user_identifier",
            ],
        }
        if user_identifier is not None:
            params['user_identifier'] = [str(user_identifier)]
        return params

    def printURL(self, dataset, user_identifier, benchmarks):
        params = self.getDjangoParams(user_identifier)

        res = []
        for k, v in params.items():
            for item in v:
                res.append(k + '=' + item)
        param_string = "&".join(res)

        url = (
            self.db_url + "?{}"
        ).format(param_string)

        print("Result URL => " + url)


registerResultURL("django", DjangoURLPrinter)
