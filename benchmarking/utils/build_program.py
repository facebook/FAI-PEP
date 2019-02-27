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

import os
import pkg_resources

from .custom_logger import getLogger
from .subprocess_with_logger import processRun


def buildProgramPlatform(dst, repo_dir, framework, frameworks_dir,
                         platform, *args):
    script = getBuildScript(framework, frameworks_dir, platform, dst)
    dst_dir = os.path.dirname(dst)
    if os.path.isfile(dst):
        os.remove(dst)
    elif not os.path.isdir(dst_dir):
        os.makedirs(dst_dir)

    if os.name == "nt":
        result, _ = processRun([script, repo_dir, dst])
    else:
        cmds = ['sh', script, repo_dir, dst]
        if args:
            cmds.extend(list(args))
        result, _ = processRun(cmds)
    if os.path.isfile(dst):
        os.chmod(dst, 0o777)
    getLogger().info('\n'.join(result))
    for r in result:
        getLogger().info("{}".format(r))

    if not os.path.isfile(dst) and \
            (not (os.path.isdir(dst) and platform.startswith("ios"))):
        getLogger().error(
            "Build program using script {} failed.".format(script))
        return False
    return True


def getBuildScript(framework, frameworks_dir, platform, dst):
    if frameworks_dir:
        try:
            build_script = _readFromPath(framework, frameworks_dir, platform, dst)
        except BaseException as e:
            getLogger().info("We will load from binary due to {}.".format(e))
            build_script = _readFromBinary(framework, frameworks_dir, platform, dst)
    else:
        try:
            build_script = _readFromBinary(framework, frameworks_dir, platform, dst)
        except BaseException as e:
            getLogger().info("We will load from old default path due to {}.".format(e))
            frameworks_dir = str(os.path.dirname(os.path.realpath(__file__))
                + "/../../specifications/frameworks")
            build_script = _readFromPath(framework, frameworks_dir, platform, dst)

    return build_script


def _readFromPath(framework, frameworks_dir, platform, dst):
    # if user provide frameworks_dir, we want to validate its correctness.
    assert os.path.isdir(frameworks_dir), \
        "{} must be specified.".format(frameworks_dir)
    framework_dir = frameworks_dir + "/" + framework
    assert os.path.isdir(framework_dir), \
        "{} must be specified.".format(framework_dir)
    platform_dir = framework_dir + "/" + platform
    build_script = None
    if os.path.isdir(platform_dir):
        if os.path.isfile(platform_dir + "/build.sh"):
            build_script = platform_dir + "/build.sh"
    if build_script is None:
        # Ideally, should check the parent directory until the
        # framework directory. Save this for the future
        build_script = framework_dir + "/build.sh"
        getLogger().warning("Directory {} ".format(platform_dir)
                            + "doesn't exist. Use "
                            + "{} instead".format(framework_dir))
    assert os.path.isfile(build_script), \
        "Cannot find build script in {} for ".framework_dir + \
        "platform {}".format(platform)

    return build_script


def _readFromBinary(framework, frameworks_dir, platform, dst):
    script_path = os.path.join("specifications/frameworks",
        framework, platform, "build.sh")
    if not pkg_resources.resource_exists("__main__", script_path):
        raise Exception(
            "cannot find the build script in the binary under {}.".format(script_path))
    raw_build_script = pkg_resources.resource_string("__main__", script_path)
    if not os.path.exists(os.path.dirname(dst)):
        os.makedirs(os.path.dirname(dst))
    with open(os.path.join(os.path.dirname(dst), "build.sh"), "w") as f:
        f.write(raw_build_script.decode("utf-8"))
    build_script = f.name

    return build_script
