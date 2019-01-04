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
import subprocess
import sys
from threading import Timer

from .custom_logger import getLogger
from .utilities import setRunStatus


def processRun(*args, **kwargs):
    getLogger().info("Running: %s", ' '.join(*args))
    err_output = None
    try:
        log_output = False
        if "log_output" in kwargs:
            log_output = kwargs["log_output"]
            del kwargs["log_output"]
        non_blocking = False
        output = None
        if "non_blocking" in kwargs and kwargs["non_blocking"]:
            non_blocking = True
            del kwargs["non_blocking"]
        if non_blocking:
            # timeout is not useful
            if "timeout" in kwargs:
                del kwargs["timeout"]
            _Popen(*args, **kwargs)
            return [], None
        else:
            patterns = []
            if "patterns" in kwargs:
                patterns = kwargs["patterns"]
                del kwargs["patterns"]
            timeout = None
            if "timeout" in kwargs:
                timeout = kwargs["timeout"]
                del kwargs["timeout"]
            ps = _Popen(*args, **kwargs)
            t = None
            if timeout:
                t = Timer(timeout, _kill, [ps, ' '.join(*args)])
                t.start()
            output, match = _getOutput(ps, patterns)
            ps.stdout.close()
            if match:
                # if the process is terminated by mathing output,
                # assume the process is executed successfully
                ps.terminate()
                status = 0
            else:
                # wait for the process to terminate
                status = ps.wait()
            if t is not None:
                t.cancel()
            if log_output or status != 0:
                getLogger().info('\n'.join(output))
            if status == 0:
                return output, None
            else:
                setRunStatus(1)
                return [], '\n'.join(output)

    except subprocess.CalledProcessError as e:
        err_output = e.output.decode("utf-8", "ignore")
        getLogger().error("Command failed: {}".format(err_output))
    except Exception:
        getLogger().error("Unknown exception {}: {}".format(sys.exc_info()[0],
                                                            ' '.join(*args)))
        err_output = "{}".format(sys.exc_info()[0])
    setRunStatus(1)
    return [], err_output


def _Popen(*args, **kwargs):
    ps = subprocess.Popen(*args, bufsize=-1, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          universal_newlines=True, **kwargs)
    # We set the buffer size to system default.
    # this is not really recommended. However, we need to stream the
    # output as they are available. So we do this. But, if the data
    # comes in too fast and there is no time to consume them, the output
    # may be truncated. Now, add a buffer to reduce the problem.
    # will see whether this is indeed an issue later on.
    return ps


def _getOutput(ps, patterns):
    if not isinstance(patterns, list):
        patterns = [patterns]
    lines = []
    match = False
    while True:
        line = ps.stdout.readline()
        if not line:
            break
        nline = line.rstrip()
        try:
            # decode the string if decode exists
            decoded_line = nline.decode('utf-8')
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


def _kill(p, cmd):
    try:
        p.kill()
    except OSError:
        pass  # ignore
    getLogger().error("Process timed out: {}".format(cmd))
    setRunStatus(1)
