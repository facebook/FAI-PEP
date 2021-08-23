from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import urllib

from remote.url_printer_base import URLPrinterBase
from remote.url_printer_base import registerResultURL


DJANGO_SUB_URL = "benchmark/visualize"

DISPLAY_COLUMNS = [
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
]


class DjangoURLPrinter(URLPrinterBase):
    def __init__(self, args):
        self.args = args
        self.db_url = os.path.join(self.args.server_addr, DJANGO_SUB_URL)

    def getColumnSelParams(self):
        col_sel_params = []
        for display_column in DISPLAY_COLUMNS:
            col_param = {
                "name": "columns",
                "value": display_column,
            }
            col_sel_params.append(col_param)
        return col_sel_params

    def getGraphConfParams(self):
        graph_conf_params = [
            {
                "name": "graph-type-dropdown",
                "value": "bar-graph",
            },
            {
                "name": "rank-column-dropdown",
                "value": "p10",
            },
        ]
        return graph_conf_params

    def getFilterParams(self, user_identifier):
        if user_identifier is None:
            return {}

        filter_params = {
            "condition": "AND",
            "rules": [
                {
                    "id": "user_identifier",
                    "field": "user_identifier",
                    "type": "string",
                    "input": "text",
                    "operator": "equal",
                    "value": str(user_identifier),
                }
            ],
            "valid": True,
        }
        return filter_params

    def getDjangoParams(self, user_identifier):
        col_sel_params = self.getColumnSelParams()
        graph_conf_params = self.getGraphConfParams()
        filter_params = self.getFilterParams(user_identifier)

        params = {
            "sort": "-p10",
            "selection_form": json.dumps(col_sel_params + graph_conf_params),
            "filters": json.dumps(filter_params),
        }

        return params

    def printURL(self, dataset, user_identifier, benchmarks):
        params = self.getDjangoParams(user_identifier)

        try:
            # pytyon 2
            param_string = urllib.urlencode(params)
        except Exception:
            # python 3
            param_string = urllib.parse.urlencode(params)

        url = (self.db_url + "?{}").format(param_string)

        print("Result URL => " + url)


registerResultURL("django", DjangoURLPrinter)
