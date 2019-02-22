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
            session = requests.Session()
            # set to False here otherwise it will get stuck when use multiprocessing
            session.trust_env = False
            result = session.post(url, **kwargs)
            result.raise_for_status()
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
        value = ast.literal_eval(value)
    except ValueError:
        getLogger().error("Failed to parse kwarg str: {}".format(kwarg_str))
    return key, value


# run_status == 0: success
# run_status == 1: user error
# run_status == 2: harness error
# run_status == 3: both user and harness error
run_status = 0


def getRunStatus():
    return run_status


def setRunStatus(status, overwrite=False):
    global run_status
    if overwrite:
        run_status = status
    else:
        run_status = run_status | status


def getMeta(args, platform):
    meta = None
    if not args.frameworks_dir:
        meta_file = os.path.join("specifications/frameworks",
                                 args.framework, platform,
                                 "meta.json")
        if pkg_resources.resource_exists("__main__", meta_file):
            meta = json.loads(pkg_resources.resource_string("__main__", meta_file))
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
