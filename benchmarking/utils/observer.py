#!/usr/bin/env python

##############################################################################
# Copyright 2019-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import json


# converts the passed in fields into one of the formats expected by the data converter
# and prepends the identifer to the json string
def emitMetric(identifier="PytorchObserver", **kwargs):
    data = {}
    # check basic fields in all formats are present
    if "type" not in kwargs or "metric" not in kwargs or "unit" not in kwargs:
        return ""
    data["type"] = kwargs["type"]
    data["metric"] = kwargs["metric"]
    data["unit"] = kwargs["unit"]
    # fields in value format
    if "value" in kwargs:
        data["value"] = kwargs["value"]
        return "{} {}".format(identifier, json.dumps(data))
    # fields in info format
    if "info_string" in kwargs:
        data["info_string"] = kwargs["info_string"]
        return "{} {}".format(identifier, json.dumps(data))
    # fields in summary format
    # summary is a list of [p0, p10, p50, p90, p100, mean, stdev, MAD]
    if "num_runs" in kwargs and "summary" in kwargs and len(kwargs["summary"]) == 8:
        data["num_runs"] = kwargs["num_runs"]
        summaryMapping = {
            "p0": 0,
            "p10": 1,
            "p50": 2,
            "p90": 3,
            "p100": 4,
            "mean": 5,
            "stdev": 6,
            "MAD": 7,
        }
        data["summary"] = {}
        for key, idx in summaryMapping.items():
            data["summary"][key] = kwargs["summary"][idx]
        return "{} {}".format(identifier, json.dumps(data))
    # invalid set of fields was passed in
    return ""
