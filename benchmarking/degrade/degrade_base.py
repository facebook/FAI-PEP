#!/usr/bin/env python

##############################################################################
# Copyright 2021-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from typing import TypedDict


class DegradeBase(object):
    """Base class for platform-specific "degrade" tools to be used to apply cpu or memory device constraints to a benchmark run.

    The implementation-specific constraints are specified by a dictionary containing a "cpu" and / or "memory" dictionary entry.

    For example:
        {
            "cpu": {
                "count": "4",
            },
            "memory": {
                "limit": "2000000KB",
            },
            "report": true,
        }

    This class also acts as a default no-op implementation in the case that no implementation is registered for a given platform.
    """

    def __init__(self, platform_util, constraints=None):
        """Specify a dictionary containing "cpu" or "memory" options to a degrade tool to apply device constraints to the benchmark run

        Args:
            platform_util: (object)  Platform-specific Device identifier object, such as adb
            constraints (dict):     Dictionary containing a "cpu" and / or "memory" dictionary of platform / implementation-specific device contraint options.

        Notes:
            The args value may also be passed to setArgs() directly if desired.

        """
        self.util = platform_util
        if constraints is not None:
            self.specifyConstraints(constraints)

    def __enter__(self):
        self.applyConstraints()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.resetConstraints()

    def specifyConstraints(self, constraints):
        """Specify a dictionary containing "cpu" or "memory" options to a degrade tool to apply device constraints to the benchmark run

        Args:
            constraints (dict):    Dictionary containing a "cpu" and / or "memory" dictionary of platform / implementation-specific device contraint options.

        Notes:
            The args value may also be passed to the constructor instead of to setArgs() if desired.
        """
        pass

    def applyConstraints(self):
        """Apply any cpu / memory constraints set previously"""
        pass

    def resetConstraints(self):
        """Reset device to defaults (remove any constraints applied previously)."""
        pass

    def logConstraints(self):
        pass


class DegradeEntries(TypedDict):
    platform: str
    degrade: DegradeBase


default_degrade = DegradeBase

degrade_table: DegradeEntries = {}


def registerDegrade(platform: str, degrade: DegradeBase):
    """Register a platform-specific DegradeBase implementation.

    Args:
        platform (str):         Name of the plaform (eg. "android", "ios").
        degrade (DegradeBase):  Implementaton drived from DegradeBase.
    """
    global degrade_table
    degrade_table[platform] = degrade


def getDegrade(platform: str) -> DegradeBase:
    """Lookup and return a registered platform-specific implementation of DegradeBase.

    Args:
        platform (str): Name of the plaform (eg. "android", "ios").

    Returns:
        A matching DegradeBase implementation or the default implementation if none.
    """
    global degrade_table
    global default_degrade
    if platform in degrade_table:
        return degrade_table[platform]

    return default_degrade
