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
    if True:
    # try:
        output = None
        if "non_blocking" in kwargs and kwargs["non_blocking"]:
            subprocess.Popen(*args)
            return "", None
        else:
            output_raw = subprocess.check_output(*args,
                                                 stderr=subprocess.STDOUT,
                                                 **kwargs)
            # without the decode/encode the string cannot be printed out
            output = output_raw.decode("utf-8", "ignore")
        return output, None
    '''
    except subprocess.CalledProcessError as e:
        err_output = e.output.decode("utf-8", "ignore")
        getLogger().error("Command failed: {}".format(err_output))
    except Exception:
        getLogger().error("Unknown exception {}: {}".format(sys.exc_info()[0],
                                                            ' '.join(*args)))
        err_output = "{}".format(sys.exc_info()[2]
    '''
    return None, err_output
