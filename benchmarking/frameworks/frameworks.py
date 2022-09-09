#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

from .caffe2.caffe2 import Caffe2Framework
from .framework_base import FrameworkBase
from .generic.generic import GenericFramework
from .glow.glow import GlowFramework
from .oculus.oculus import OculusFramework
from .pytorch.pytorch import PytorchFramework
from .tflite.tflite import TFLiteFramework

frameworks = {
    "caffe2": Caffe2Framework,
    "generic": GenericFramework,
    "oculus": OculusFramework,
    "pytorch": PytorchFramework,
    "tflite": TFLiteFramework,
    "glow": GlowFramework,
}


def getFrameworks():
    global frameworks
    return frameworks


def registerFramework(name, framework_class):
    global frameworks
    assert issubclass(framework_class, FrameworkBase)
    frameworks[name] = framework_class
