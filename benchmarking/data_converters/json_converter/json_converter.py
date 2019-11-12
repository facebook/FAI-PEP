#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import collections
import json

from data_converters.data_converter_base import DataConverterBase
from utils.custom_logger import getLogger


class JsonConverter(DataConverterBase):
    def __init__(self):
        super(JsonConverter, self).__init__()

    def getName(self):
        return "json_converter"

    def collect(self, data, args=None):
        rows = self._prepareData(data)
        results = []
        valid_run_idxs = []
        for row in rows:
            try:
                result = json.loads(row)
                if ("type" in result and result["type"] == "NET"
                        and "value" in result) \
                        or ("NET" in result):  # for backward compatibility
                    valid_run_idxs.append(len(results))
                results.append(result)
            except Exception as e:
                # bypass one line
                getLogger().info(
                    "Skip one row %s \n Exception: %s" %
                    (row, str(e))
                )
                pass
        if len(valid_run_idxs) > 0:
            # strip data not yet in a valid range
            # here it is assumed the NET metric appears earlier than
            # other metrics
            results = results[valid_run_idxs[0]:]
        return results, valid_run_idxs

    def convert(self, data):
        details = collections.defaultdict(
            lambda: collections.defaultdict(list))
        for d in data:
            if "type" in d and "metric" in d and "unit" in d:
                # new format
                key = d["type"] + " " + d["metric"]
                if "info_string" in d:
                    if "info_string" in details[key]:
                        old_string = details[key]["info_string"]
                        new_string = d["info_string"]
                        if old_string != new_string:
                            getLogger().warning("info_string values "
                                                "for {} ".format(key)
                                                + "do not match.\n"
                                                + "Current info_string: "
                                                + "{}\n ".format(old_string)
                                                + "does not match new "
                                                + "info_string: "
                                                + "{}".format(new_string))
                    else:
                        details[key]["info_string"] = d["info_string"]
                if "value" in d:
                    details[key]["values"].append(float(d["value"]))
                if "num_runs" in d:
                    details[key]["num_runs"] = d["num_runs"]
                if "summary" in d:
                    details[key]["summary"] = d["summary"]
                self._updateOneEntry(details[key], d, "type")
                self._updateOneEntry(details[key], d, "metric")
                self._updateOneEntry(details[key], d, "unit")
            else:
                # for backward compatibility purpose
                # will remove after some time
                for k, v in d.items():
                    if not isinstance(v, dict):
                        # prevent some data corruption
                        continue
                    for kk, vv in v.items():
                        key = k + " " + kk
                        if "info_string" in vv:
                            if "info_string" in details[key]:
                                assert details[key]["info_string"] == \
                                    vv["info_string"], \
                                    "info_string values for {} ".format(key) + \
                                    "do not match.\n" + \
                                    "Current info_string:\n{}\n ".format(
                                    details[key]["info_string"]) + \
                                    "does not match new info_string:\n{}".format(
                                    vv["info_string"])
                            else:
                                details[key]["info_string"] = vv["info_string"]
                        else:
                            details[key]["values"].append(float(vv["value"]))
                        details[key]["type"] = k
                        # although it is declared as list
                        details[key]["metric"] = kk
                        details[key]["unit"] = str(vv["unit"])
        return details

    def _updateOneEntry(self, detail, d, k):
        if k in detail:
            assert detail[k] == d[k], \
                "Field {} does not match in different entries".format(k)
        else:
            detail[k] = d[k]
