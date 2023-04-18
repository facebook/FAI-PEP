#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import select
import signal
import subprocess
import sys
import time
from threading import Timer

from .custom_logger import getLogger
from .utilities import getRunKilled, getRunTimeout, setRunStatus, setRunTimeout


def processRun(*args, **kwargs):
    if "process_key" not in kwargs:
        kwargs["process_key"] = ""
    retryCount = 3
    if "retry" in kwargs:
        retryCount = kwargs["retry"]
    while retryCount > 0:
        # reset run status overwritting error
        # from prior run
        # Use temporary process key for each retry to avoid overwriting global status where process_key=""
        setRunStatus(0, overwrite=True, key=kwargs["process_key"] + "_retry")
        sleep = kwargs.get("retry_sleep")
        if sleep:
            getLogger().info("Sleeping for {}".format(sleep))
            time.sleep(sleep)
        processRunRetryKwargs = kwargs
        processRunRetryKwargs["process_key"] = kwargs["process_key"] + "_retry"
        ret = _processRun(*args, **processRunRetryKwargs)
        # break out if the run succeeded
        if ret[1] is None:
            setRunStatus(0, key=kwargs["process_key"])
            if not kwargs.get("silent", False):
                getLogger().info("Process Succeeded: %s", " ".join(*args))
            break
        # don't retry for errors which we know will
        # fail again (ie. timeouts)
        if getRunTimeout():
            getLogger().info("Process Failed: %s", " ".join(*args))
            break
        retryCount -= 1
        if retryCount > 0:
            getLogger().info(
                f"Process Failed (will retry {retryCount} more times): {' '.join(*args)}"
            )
        else:
            # TODO: Early stopping -- stop job after a subprocess fails multiple times.
            # fail the whole job
            if not kwargs.get("silent", False):
                getLogger().info("Process Failed.")
                if not kwargs.get("ignore_status", False):
                    setRunStatus(1)
    return ret


def _processRun(*args, **kwargs):
    if not kwargs.get("silent", False):
        getLogger().info(">>>>>> Running: %s", " ".join(*args))
    err_output = None
    try:
        run_async = False
        if "async" in kwargs:
            run_async = kwargs["async"]
        non_blocking = False
        if "non_blocking" in kwargs and kwargs["non_blocking"]:
            non_blocking = True
        if non_blocking:
            _Popen(*args, **kwargs)
            return [], None
        timeout = None
        if "timeout" in kwargs:
            timeout = kwargs["timeout"]
        ps = _Popen(*args, **kwargs)
        t = None
        if timeout:
            t = Timer(timeout, _kill, [ps, " ".join(*args), kwargs["process_key"]])
            t.start()
        if run_async:
            # when running the process asyncronously we return the
            # popen object and timer for the timeout as a tuple
            # it is the responsibility of the caller to pass this
            # tuple into processWait in order to gather the output
            # from the process
            return (ps, t), None
        return processWait((ps, t), **kwargs)
    except subprocess.CalledProcessError as e:
        err_output = e.output.decode("utf-8", errors="replace")
        getLogger().error("Command failed: {}".format(err_output))
    except Exception:
        getLogger().error(
            "Unknown exception {}: {}".format(sys.exc_info()[0], " ".join(*args))
        )
        err_output = "{}".format(sys.exc_info()[0])
    return [], err_output


def processWait(processAndTimeout, **kwargs):
    silent = kwargs.get("silent", False)
    try:
        ps, t = processAndTimeout
        process_key = ""
        if "process_key" in kwargs:
            process_key = kwargs["process_key"]
        log_output = False
        if "log_output" in kwargs:
            log_output = kwargs["log_output"]
        ignore_status = False
        if "ignore_status" in kwargs:
            ignore_status = kwargs["ignore_status"]
        patterns = []
        if "patterns" in kwargs:
            patterns = kwargs["patterns"]
        output, match = _getOutput(ps, patterns, process_key=process_key)
        ps.stdout.close()
        if match:
            # if the process is terminated by mathing output,
            # assume the process is executed successfully
            ps.terminate()
            status = 0
        else:
            # wait for the process to terminate or for a kill request
            while not getRunKilled():
                try:
                    status = ps.wait(timeout=15.0)
                    break
                except subprocess.TimeoutExpired:
                    pass
            # check if we exitted loop due to a timeout request
            if getRunKilled():
                getLogger().info("Process was killed at user request")
                ps.terminate()
                status = 0
        if t is not None:
            t.cancel()
        if log_output or (status != 0 and not ignore_status):
            if status != 0 and not ignore_status:
                if not silent:
                    getLogger().info("Process exited with status: {}".format(status))
                setRunStatus(1, key=process_key)
            if "filter" in kwargs:
                output = _filterOutput(output, kwargs["filter"])
            if not silent:
                getLogger().info(
                    "\n\nProgram Output:\n{}\n{}\n{}\n".format(
                        "=" * 80, "\n".join(output), "=" * 80
                    )
                )
        if status == 0 or ignore_status:
            setRunStatus(0, key=process_key)
            return output, None
        else:
            setRunStatus(1, key=process_key)
            return [], "\n".join(output)
    except subprocess.CalledProcessError as e:
        err_output = e.output.decode("utf-8", errors="replace")
        getLogger().error("Command failed: {}".format(err_output))
    except Exception:
        err_output = "{}".format(sys.exc_info()[0])
        getLogger().error("Unknown exception {}".format(sys.exc_info()[0]))
    return [], err_output


def _filterOutput(output, match_list):
    length = len(output)
    for i, line in enumerate(output[::-1]):
        for match in match_list:
            if match in line:
                del output[length - i - 1]
                break
    return output


def _Popen(*args, **kwargs):
    # only allow allowlisted args to be passed into popen
    customArgs = {}
    allowlist = ["env", "shell"]
    for arg in allowlist:
        if arg in kwargs:
            customArgs[arg] = kwargs[arg]

    ps = subprocess.Popen(
        *args,
        bufsize=-1,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        preexec_fn=os.setsid,
        errors="replace",
        **customArgs,
    )
    # We set the buffer size to system default.
    # this is not really recommended. However, we need to stream the
    # output as they are available. So we do this. But, if the data
    # comes in too fast and there is no time to consume them, the output
    # may be truncated. Now, add a buffer to reduce the problem.
    # will see whether this is indeed an issue later on.
    return ps


def _getOutput(ps, patterns, process_key=""):
    if not isinstance(patterns, list):
        patterns = [patterns]

    poller = select.poll()
    poller.register(ps.stdout)

    lines = []
    match = False
    while not getRunKilled(process_key):
        # Try to get output from binary if possible
        # If not possible then loop
        # and recheck run killed contidion
        if poller.poll(15.0):
            line = ps.stdout.readline()
        else:
            continue
        if not line:
            break
        nline = line.rstrip()
        try:
            # decode the string if decode exists
            decoded_line = nline.decode("utf-8", errors="replace")
            nline = decoded_line
        except Exception:
            pass
        lines.append(nline)
        for pattern in patterns:
            if pattern.match(nline):
                match = True
                break
        if match:
            break
    return lines, match


def _kill(p, cmd, processKey):
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except OSError:
        pass  # ignore
    getLogger().error("Process timed out: {}".format(cmd))
    setRunStatus(1, key=processKey)
    setRunTimeout()
