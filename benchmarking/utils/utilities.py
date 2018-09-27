#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import copy
import datetime
import os
import re
import requests
from six import string_types
import sys
from time import sleep

from .custom_logger import getLogger


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


def getFilename(name):
    filename = name.replace(' ', '-').replace('/', '-').replace('\\', '-')
    return "".join([c for c in filename
                    if c.isalpha() or c.isdigit() or
                    c == '_' or c == '.' or c == '-']).rstrip()


def getPythonInterpreter():
    return sys.executable


def deepMerge(tgt, src):
    if isinstance(src, list):
        # only handle simple lists
        for item in src:
            if item not in tgt:
                tgt.append(copy.deepcopy(item))
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
    if re.match("^[A-Za-z0-9_/.~-]+$", s):
        return s
    elif os.name == "nt":
        # escape " with \"
        return '"' + s.replace('"', '\\"') + '"'
    else:
        return "'" + s + "'"


def requestsData(url, **kwargs):
    delay = 0
    total_delay = 0
    timeout = -1
    if "timeout" in kwargs:
        timeout = kwargs["timeout"]
    result = None
    while True:
        try:
            result = requests.post(url, **kwargs)
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
