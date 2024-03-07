#!/usr/bin/env python

# pyre-unsafe

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
import socket
import sys
import tempfile
import uuid
import zipfile
from time import sleep

import aiohttp
import certifi
import pkg_resources
import requests
from six import string_types
from utils.custom_logger import getLogger

# Status codes for benchmark
SUCCESS_FLAG = 0
USER_ERROR_FLAG = 1
HARNESS_ERROR_FLAG = 2
USER_AND_HARNESS_ERROR_FLAG = 3
TIMEOUT_FLAG = 1 << 8
KILLED_FLAG = 1 << 9
# Mask to expose only external status bits
EXTERNAL_STATUS_MASK = 0xFF


class BenchmarkException(Exception):
    """Base class for all benchmark exceptions."""

    pass


class DownloadException(BenchmarkException):
    """Raised where exception occurs when downloading benchmark files."""

    pass


class DownloadNotFoundException(BenchmarkException):
    """Raised where exception occurs when downloading benchmark files."""

    pass


class BenchmarkArgParseException(BenchmarkException):
    """Raised where benchmark arguments could not be parsed or are invalid."""

    pass


class BenchmarkUnsupportedDeviceException(BenchmarkException):
    """Raised where benchmark arguments specify an invalid device."""

    pass


class BenchmarkInvalidBinaryException(BenchmarkException):
    """Raised where benchmark arguments specify an invalid binary."""

    pass


def check_is_json(json_str):
    try:
        json.loads(json_str)
        return True
    except ValueError:
        return False


def getBenchmarks(json_input, framework=None):
    if os.path.isfile(json_input):
        with open(json_input, "r") as f:
            content = json.load(f)
    elif check_is_json(json_input):
        content = json.loads(json_input)
    else:
        raise Exception(f"specified benchmark file doesn't exist: {json_input}")

    benchmarks = []
    if "benchmarks" in content:
        path = os.path.abspath(os.path.dirname(json_input))
        for benchmark_file in content["benchmarks"]:
            filename = os.path.join(path, benchmark_file)
            assert os.path.isfile(filename), "Benchmark {} doesn't exist".format(
                filename
            )
            with open(filename, "r") as f:
                cnt = json.load(f)
                if framework and "model" in cnt and "framework" not in cnt["model"]:
                    # do not override the framework specified in the json
                    cnt["model"]["framework"] = framework
                benchmarks.append({"filename": filename, "content": cnt})
    else:
        if framework and "model" in content:
            content["model"]["framework"] = framework
        benchmarks.append({"filename": json_input, "content": content})
    return benchmarks


def getDirectory(commit_hash, commit_time):
    dt = datetime.datetime.utcfromtimestamp(commit_time)
    directory = os.path.join(str(dt.year), str(dt.month), str(dt.day), commit_hash)
    return directory


def getCommand(command):
    exe = command[0]
    args = [x if x.isdigit() else "'" + x + "'" for x in command[1:]]
    cmd = exe + " " + " ".join(args)
    return cmd


def getFilename(name, **kwargs):
    replace_pattern = {" ": "-", "\\": "-", ":": "-", "/": "-"}
    if "replace_pattern" in kwargs:
        replace_pattern = kwargs["replace_pattern"]
    filename = name
    for orig_pattern, repl_pattern in replace_pattern.items():
        filename = filename.replace(orig_pattern, repl_pattern)
    res = "".join(
        [
            c
            for c in filename
            if c.isalpha()
            or c.isdigit()
            or c == "_"
            or c == "."
            or c == "-"
            or c == "/"
        ]
    ).rstrip()
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


def ca_cert():
    """Get valid ca_cert path for requests"""
    ca_cert_path = os.environ.get("CA_CERT_PATH")
    if not ca_cert_path or not os.path.exists(ca_cert_path):
        os.environ["CA_CERT_PATH"] = certifi.where()
    return os.environ["CA_CERT_PATH"]


def requestsData(url, **kwargs):
    delay = 0
    total_delay = 0
    timeout = -1
    if "timeout" in kwargs:
        timeout = kwargs["timeout"]
    retry = kwargs.pop("retry", True)
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
                # This session object can be reused.
                # If the CA_CERT file has changed it will not be updated implicitly.
                session.verify = ca_cert()
                result = session.post(url, **kwargs)
            if result.status_code != 200:
                getLogger().error(
                    "Post request failed, receiving code {}".format(result.status_code)
                )
            else:
                if delay > 0:
                    getLogger().info("Post request successful")
                return result
        except requests.exceptions.SSLError:
            getLogger().exception("Post SSL verification failed")
        except requests.ConnectionError:
            getLogger().exception("Post Connection failed")
        except requests.exceptions.ReadTimeout:
            getLogger().exception("Post Readtimeout")
        except requests.exceptions.ChunkedEncodingError:
            getLogger().exception("Post ChunkedEncodingError")
        if not retry:
            break
        delay = delay + 1 if delay <= 5 else delay
        sleep_time = 1 << delay
        getLogger().info("wait {} seconds. Retrying...".format(sleep_time))
        sleep(sleep_time)
        total_delay += sleep_time
        if timeout > 0 and total_delay > timeout:
            break
    getLogger().error(
        "Failed to post to {}, retrying after {} seconds...".format(url, total_delay)
    )
    return result


async def asyncRequestsData(loop, url, **kwargs):
    delay = 0
    total_delay = 0
    timeout = -1
    if "timeout" in kwargs:
        timeout = kwargs["timeout"]
    retry = kwargs.pop("retry", True)
    result = None
    while True:
        try:
            async with aiohttp.ClientSession(loop=loop) as session:
                async with session.post(url, **kwargs) as result:
                    text = await result.text()
                    if result.status != 200:
                        text = json.loads(text)
                        getLogger().error(
                            f"Async post request returned status code {result.status}. Reason: {result.reason} Message: {text.get('error',{})}"
                        )
                    else:
                        # getLogger().info(result.status)
                        if delay > 0:
                            getLogger().info("Async post request successful")
                        return result
        except Exception:
            getLogger().exception("Exception occured during async request!")
        if not retry:
            break
        delay = delay + 1 if delay <= 5 else delay
        sleep_time = 1 << delay
        getLogger().info("wait {} seconds. Retrying...".format(sleep_time))
        sleep(sleep_time)
        total_delay += sleep_time
        if timeout > 0 and total_delay > timeout:
            break
    getLogger().error(
        "Failed to post to {}, retrying after {} seconds...".format(url, total_delay)
    )
    return result


def requestsJson(url, **kwargs):
    try:
        result = requestsData(url, **kwargs)
        if result and result.status_code == 200:
            result_json = result.json()
            return result_json
    except ValueError as e:
        getLogger().error("Cannot decode json {}".format(e.output))

    getLogger().error("Failed to retrieve json from {}".format(url))
    return {}


async def asyncRequestsJson(loop, url, **kwargs):
    try:
        result = await asyncRequestsData(loop, url, **kwargs)
        if result and result.status == 200:
            async with result:
                result_json = await result.text()
                return json.loads(result_json)
    except ValueError as e:
        getLogger().error("Cannot decode json {}".format(e.output))

    getLogger().error("Failed to retrieve json from {}".format(url))
    return {}


def parse_kwarg(kwarg_str):
    key, value = kwarg_str.split("=")
    try:
        value = ast.literal_eval("'" + value + "'")
    except ValueError:
        getLogger().error("Failed to parse kwarg str: {}".format(kwarg_str))
    return key, value


def getModelName(model):
    # given benchmark model entry parse model name, returns string.
    if model["framework"] == "caffe2":
        model_file_name = model["files"]["predict"]["filename"]
    elif model.get("files", {}).get("model", {}).get("filename", None):
        model_file_name = model["files"]["model"]["filename"]
    elif "name" in model:
        model_file_name = model["name"]
    else:
        model_file_name = "model"
    model_name = os.path.splitext(model_file_name)[0].replace(" ", "_")
    return model_name


# Run status
run_statuses = {}


def _getRawRunStatus(key=""):
    global run_statuses
    return run_statuses.get(key, 0)


def _setRawRunStatus(status, key=""):
    global run_statuses
    run_statuses[key] = status


def getRunStatus(key=""):
    return _getRawRunStatus(key) & EXTERNAL_STATUS_MASK


def setRunStatus(status, overwrite=False, key=""):
    if overwrite:
        _setRawRunStatus(status, key)
    else:
        _setRawRunStatus(_getRawRunStatus(key) | status, key)


def getRunTimeout(key=""):
    return _getRawRunStatus(key) & TIMEOUT_FLAG == TIMEOUT_FLAG


def setRunTimeout(timedOut=True, key=""):
    if timedOut:
        _setRawRunStatus(_getRawRunStatus(key) | TIMEOUT_FLAG, key)
    else:
        _setRawRunStatus(_getRawRunStatus(key) & ~TIMEOUT_FLAG, key)


def getRunKilled(key=""):
    return _getRawRunStatus(key) & KILLED_FLAG == KILLED_FLAG


def setRunKilled(killed=True, key=""):
    if killed:
        _setRawRunStatus(_getRawRunStatus(key) | KILLED_FLAG, key)
    else:
        _setRawRunStatus(_getRawRunStatus(key) & ~KILLED_FLAG, key)


def getMeta(args, platform):
    meta = None
    if not args.frameworks_dir:
        meta_file = os.path.join(
            "specifications/frameworks", args.framework, platform, "meta.json"
        )
        if "aibench" in sys.modules and pkg_resources.resource_exists(
            "aibench", meta_file
        ):
            meta = json.loads(pkg_resources.resource_string("aibench", meta_file))
            return meta
        else:
            # look for files in the old default place
            old_default = str(
                os.path.dirname(os.path.realpath(__file__))
                + "/../../specifications/frameworks"
            )
            meta_file = os.path.join(old_default, args.framework, platform, "meta.json")
    else:
        meta_file = os.path.join(
            args.frameworks_dir, args.framework, platform, "meta.json"
        )
    if os.path.isfile(meta_file):
        with open(meta_file, "r") as f:
            meta = json.load(f)
    return meta


def getMachineId():
    ident = socket.getfqdn()
    if len(ident) == 0 or ident == "localhost":
        ident = uuid.uuid1().hex
    return ident


adhoc_configs = {
    "generic": "specifications/models/generic/adhoc.json",
    "opbench": "specifications/models/generic/adhoc_microbenchmarks.json",
}


def unpackAdhocFile(configName="generic"):
    if configName not in adhoc_configs:
        return "", False

    fd, path = tempfile.mkstemp(prefix="aibench")
    with pkg_resources.resource_stream("aibench", adhoc_configs[configName]) as stream:
        with os.fdopen(fd, "wb") as f:
            f.write(stream.read())

    return path, True


def zip_files(input, output: str):
    """
    Archive files or folder for uploading.
    Input can be file/folder path or list of paths.
    Folder hierarchy will be preserved at the folder basename level.
    """
    if not isinstance(input, list):
        input = [input]
    with zipfile.ZipFile(output, "w") as zf:
        for path in input:
            if os.path.isfile(path):
                zf.write(path, os.path.basename(path))
            elif os.path.isdir(path):
                for directory, _, files in os.walk(path):
                    arcdir = directory[directory.find(os.path.basename(path)) :]
                    zf.write(directory, arcdir)
                    for f in files:
                        fpath = os.path.join(directory, f)
                        arcfpath = os.path.join(arcdir, f)
                        zf.write(fpath, arcfpath)
            else:
                raise IOError(f"Could not zip files. {path} is not a valid path.")
