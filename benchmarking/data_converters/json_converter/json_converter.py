#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


import collections
import json
import re

from data_converters.data_converter_base import DataConverterBase
from data_converters.data_converters import registerConverter
from utils.custom_logger import getLogger


class JsonConverter(DataConverterBase):
    def __init__(self):
        super().__init__()

    @staticmethod
    def getName():
        return "json_converter"

    def collect(self, data, args=None):
        rows = self._prepareData(data)
        results = []
        valid_run_idxs = []
        for row in rows:
            try:
                pattern = r"\{.*\}"
                match = re.findall(pattern, row)
                if match is None or len(match) == 0:
                    getLogger().debug("Format not correct, skip one row %s \n" % (row))
                else:
                    result = json.loads(match[0])
                    if (
                        ("type" in result and "value" in result)
                        or ("NET" in result)
                        or ("custom_output" in result)
                    ):  # for backward compatibility
                        valid_run_idxs.append(len(results))
                    results.append(result)
            except Exception as e:
                # bypass one line
                getLogger().info("Skip one row {} \n Exception: {}".format(row, str(e)))
                pass
        if len(valid_run_idxs) > 0:
            # strip data not yet in a valid range
            # here it is assumed the NET metric appears earlier than
            # other metrics
            results = results[valid_run_idxs[0] :]
        return results, valid_run_idxs

    def convert(self, data):
        details = collections.defaultdict(lambda: collections.defaultdict(list))
        for d in data:
            if "custom_output" in d:
                table_name = d["table_name"] if "table_name" in d else "Custom Output"
                details["custom_output"][table_name].append(d["custom_output"])

            if (
                "type" in d
                and "metric" in d
                and "unit" in d
                and "custom_output" not in d
            ):
                # new format
                getLogger().info("New format")
                key = d["type"] + " " + d["metric"]
                if "info_string" in d:
                    if "info_string" in details[key]:
                        old_string = details[key]["info_string"]
                        new_string = d["info_string"]
                        if old_string != new_string:
                            getLogger().warning(
                                "info_string values " "for {} ".format(key)
                                + "do not match.\n"
                                + "Current info_string: "
                                + f"{old_string}\n "
                                + "does not match new "
                                + "info_string: "
                                + f"{new_string}"
                            )
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
                                assert (
                                    details[key]["info_string"] == vv["info_string"]
                                ), (
                                    f"info_string values for {key} "
                                    + "do not match.\n"
                                    + "Current info_string:\n{}\n ".format(
                                        details[key]["info_string"]
                                    )
                                    + "does not match new info_string:\n{}".format(
                                        vv["info_string"]
                                    )
                                )
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
            assert detail[k] == d[k], f"Field {k} does not match in different entries"
        else:
            detail[k] = d[k]


registerConverter(JsonConverter)
