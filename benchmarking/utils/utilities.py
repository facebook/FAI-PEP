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
import copy
import datetime
import json
import os
import pkg_resources
import requests
from six import string_types
import sys
from time import sleep
import socket
import uuid

from .custom_logger import getLogger


def getBenchmarks(bfile, framework=None):
    assert os.path.isfile(bfile), \
        "Specified benchmark file doesn't exist: {}".format(bfile)

    with open(bfile, 'r') as f:
        content = json.load(f)
    benchmarks = []
    if "benchmarks" in content:
        path = os.path.abspath(os.path.dirname(bfile))
        for benchmark_file in content["benchmarks"]:
            filename = os.path.join(path, benchmark_file)
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


def getDirectory(commit_hash, commit_time):
    dt = datetime.datetime.utcfromtimestamp(commit_time)
    directory = os.path.join(str(dt.year), str(dt.month), str(dt.day),
                             commit_hash)
    return directory


def getCommand(command):
    exe = command[0]
    args = [x if x.isdigit() else "'" + x + "'" for x in command[1:]]
    cmd = exe + ' ' + ' '.join(args)
    return cmd


def getFilename(name, **kwargs):
    replace_pattern = {
        " ": '-',
        "\\": '-',
        ":": '-',
        "/": '-',
    }
    if "replace_pattern" in kwargs:
        replace_pattern = kwargs["replace_pattern"]
    filename = name
    for orig_pattern, repl_pattern in replace_pattern.items():
        filename = filename.replace(orig_pattern, repl_pattern)
    res = "".join([c for c in filename
                    if c.isalpha() or c.isdigit()
                    or c == '_' or c == '.' or c == '-' or c == '/']).rstrip()
    return res


def getPythonInterpreter():
    return sys.executable


def deepMerge(tgt, src):
    if isinstance(src, list):
        # only handle simple lists
        tgt.extend(src)
    elif isinstance(src, dict):
        for name in src:
            m = src[name]
            if name not in tgt:
                tgt[name] = copy.deepcopy(m)
            else:
                deepMerge(tgt[name], m)
    else:
        # tgt has already specified a value
        # src does not override tgt
        return


def deepReplace(root, pattern, replacement):
    if isinstance(root, list):
        for idx in range(len(root)):
            item = root[idx]
            root[idx] = deepReplace(item, pattern, replacement)
    elif isinstance(root, dict):
        for name in root:
            m = root[name]
            root[name] = deepReplace(m, pattern, replacement)
    elif isinstance(root, string_types):
        return root.replace(pattern, replacement)
    return root


def getString(s):
    s = str(s)
    if os.name == "nt":
        # escape " with \"
        return '"' + s.replace('"', '\\"') + '"'
    else:
        return s


def getFAIPEPROOT():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    root_dir = os.path.join(dir_path, "../../")
    return os.path.abspath(root_dir)


def requestsData(url, **kwargs):
    delay = 0
    total_delay = 0
    timeout = -1
    if "timeout" in kwargs:
        timeout = kwargs["timeout"]
    result = None
    while True:
        try:
            """
            When we use multiprocessing to call harness from internal,
            requests.Post(url, **kwargs) will get stuck and neither proceeding
            ahead nor throwing an error. Instead, we use Session and set
            trust_env to False to solve the problem.
            Reference: https://stackoverflow.com/a/39822223
            """
            with requests.Session() as session:
                session.trust_env = False
                result = session.post(url, **kwargs)
            if result.status_code != 200:
                getLogger().error("Post request failed, receiving code {}".
                                  format(result.status_code))
            else:
                if delay > 0:
                    getLogger().info("Post request successful")
                return result
        except requests.ConnectionError as e:
            getLogger().error("Post Connection failed {}".format(e))
        except requests.exceptions.ReadTimeout as e:
            getLogger().error("Post Readtimeout {}".format(e))
        except requests.exceptions.ChunkedEncodingError as e:
            getLogger().error("Post ChunkedEncodingError {}".format(e))
        delay = delay + 1 if delay <= 5 else delay
        sleep_time = 1 << delay
        getLogger().info("wait {} seconds. Retrying...".format(sleep_time))
        sleep(sleep_time)
        total_delay += sleep_time
        if timeout > 0 and total_delay > timeout:
            break
    getLogger().error("Failed to post to {}, retrying after {} seconds...".
                      format(url, total_delay))
    return result


def requestsJson(url, **kwargs):
    try:
        result = requestsData(url, **kwargs)
        if result and result.status_code == 200:
            result_json = result.json()
            return result_json
    except ValueError as e:
        getLogger().error("Cannot decode json {}".format(e.output))

    getLogger().error("Failed to retrieve json from {}".
                      format(url))
    return {}


def parse_kwarg(kwarg_str):
    key, value = kwarg_str.split('=')
    try:
        value = ast.literal_eval("'" + value + "'")
    except ValueError:
        getLogger().error("Failed to parse kwarg str: {}".format(kwarg_str))
    return key, value


# run_statuses[key] == 0: success
# run_statuses[key] == 1: user error
# run_statuses[key] == 2: harness error
# run_statuses[key] == 3: both user and harness error
run_statuses = {}

# internal flags which will be masked out when returning the status
timeout_flag = 1 << 8

# mask to expose only external status bits
external_status_mask = 0xff


def _getRawRunStatus(key=''):
    global run_statuses
    return run_statuses.get(key, 0)


def _setRawRunStatus(status, key=''):
    global run_statuses
    run_statuses[key] = status


def getRunStatus(key=''):
    return _getRawRunStatus(key) & external_status_mask


def setRunStatus(status, overwrite=False, key=''):
    if overwrite:
        _setRawRunStatus(status, key)
    else:
        _setRawRunStatus(_getRawRunStatus(key) | status, key)


def getRunTimeout(key=''):
    return _getRawRunStatus(key) & timeout_flag == timeout_flag


def setRunTimeout(timedOut=True, key=''):
    if timedOut:
        _setRawRunStatus(_getRawRunStatus(key) | timeout_flag, key)
    else:
        _setRawRunStatus(_getRawRunStatus(key) & ~timeout_flag, key)


def getMeta(args, platform):
    meta = None
    if not args.frameworks_dir:
        meta_file = os.path.join("specifications/frameworks",
                                 args.framework, platform,
                                 "meta.json")
        if "aibench" in sys.modules and \
                pkg_resources.resource_exists("aibench", meta_file):
            meta = json.loads(
                pkg_resources.resource_string("aibench", meta_file))
            return meta
        else:
            # look for files in the old default place
            old_default = str(os.path.dirname(os.path.realpath(__file__))
                + "/../../specifications/frameworks")
            meta_file = os.path.join(old_default, args.framework,
                             platform, "meta.json")
    else:
        meta_file = os.path.join(args.frameworks_dir, args.framework,
                                 platform, "meta.json")
    if os.path.isfile(meta_file):
        with open(meta_file, "r") as f:
            meta = json.load(f)
    return meta


def getMachineId():
    ident = socket.getfqdn()
    if len(ident) == 0 or ident == 'localhost':
        ident = uuid.uuid1().hex
    return ident
