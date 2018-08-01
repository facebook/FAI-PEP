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
from .custom_logger import getLogger


def processRun(*args, **kwargs):
    getLogger().info("Running: %s", ' '.join(*args))
    err_output = None
    try:
        output = None
        if "non_blocking" in kwargs and kwargs["non_blocking"]:
            subprocess.Popen(*args)
            return "", None
        else:
            output = subprocess.check_output(*args,
                                             stderr=subprocess.STDOUT,
                                             **kwargs).\
                decode("utf-8", "ignore")
        return output, None
    except subprocess.CalledProcessError as e:
        getLogger().error("Command failed: {}".format(e.output))
        err_output = e.output.decode("utf-8", "ignore")
    except subprocess.TimeoutExpired as e:
        getLogger().error("A child process has been taken over your" +
                          "timeout = {}".format(kwargs["timeout"]))
        err_output = e.output.decode("utf-8", "ignore")
    except Exception:
        getLogger().error("Unknown failure {}: {}".format(sys.exc_info()[0],
                                                          ' '.join(*args)))
        err_output = "{}".format(sys.exc_info()[2].decode("utf-8", "ignore"))
    return None, err_output
