#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals
import ast
import json
import os
import requests
import sys
from time import sleep

# from .custom_logger import getLogger


def getBenchmarks(bfile, framework=None):
    assert os.path.isfile(bfile), \
        "Specified benchmark file doesn't exist: {}".format(bfile)

    with open(bfile, 'r') as f:
        content = json.load(f)
    benchmarks = []
    if "benchmarks" in content:
        path = os.path.abspath(os.path.dirname(bfile))
        for benchmark_file in content["benchmarks"]:
            filename = path + "/" + benchmark_file
            assert os.path.isfile(filename), \
                "Benchmark {} doesn't exist".format(filename)
            with open(filename, 'r') as f:
                cnt = json.load(f)
                if framework and "model" in cnt and \
                        "framework" not in cnt["model"]:
                    # do not override the framework specified in the json
                    cnt["model"]["framework"] = framework
                benchmarks.append({"filename": filename, "content": cnt})
    else:
        if framework and "model" in content:
            content["model"]["framework"] = framework
        benchmarks.append({"filename": bfile, "content": content})
    return benchmarks


def requestsData(url, **kwargs):
    delay = 0
    while True:
        try:
            result = requests.post(url, **kwargs)
            if result.status_code != 200:
                print("ERROR=====")
                # getLogger().error("Post request failed, receiving code {}".
                #     format(result.status_code))
            else:
                # if delay > 0:
                #     getLogger().info("Post request successful")
                return result
        except requests.ConnectionError as e:
            print("Post Connection failed {}".format(e))
        #     getLogger().error("Post Connection failed {}".format(e))
        # except requests.exceptions.ReadTimeout as e:
        #     getLogger().error("Post Readtimeout {}".format(e))
        # except requests.exceptions.ChunkedEncodingError as e:
        #     getLogger().error("Post ChunkedEncodingError {}".format(e))
        delay = delay + 1 if delay <= 5 else delay
        # getLogger().info("wait {} seconds. Retrying...".format(1 << delay))
        sleep(1 << delay)
    # getLogger().error("Failed to post to {}, retrying after {} seconds...".
    #     format(url, 1 << delay))
    return result


def requestsJson(url, **kwargs):
    try:
        result = requestsData(url, **kwargs)
        if result.status_code == 200:
            result_json = result.json()
            return result_json
    except ValueError as e:
        getLogger().error("Cannot decode json {}".format(e.output))

    getLogger().error("Failed to retrieve json from {}".
        format(url))
    return {}


def getPythonInterpreter():
    return sys.executable


def parse_kwarg(kwarg_str):
    key, value = kwarg_str.split('=')
    try:
        value = ast.literal_eval(value)
    except ValueError:
        getLogger().error("Failed to parse kwarg str: {}".format(kwarg_str))
    return key, value
