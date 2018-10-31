#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import os
import shutil

from .custom_logger import getLogger
from .subprocess_with_logger import processRun


def buildProgramPlatform(dst, repo_dir, framework, frameworks_dir, platform):
    script = _getBuildScript(framework, frameworks_dir, platform)
    dst_dir = os.path.dirname(dst)
    if os.path.isdir(dst_dir):
        shutil.rmtree(dst_dir, True)
    os.makedirs(dst_dir)

    if os.name == "nt":
        result, _ = processRun([script, repo_dir, dst])
    else:
        result, _ = processRun(['sh', script, repo_dir, dst])
    if os.path.isfile(dst):
        os.chmod(dst, 0o777)
    getLogger().info(result)

    if not os.path.isfile(dst) and \
            (not (os.path.isdir(dst) and platform.startswith("ios"))):
        getLogger().error(
            "Build program using script {} failed.".format(script))
        return False
    return True


def _getBuildScript(framework, frameworks_dir, platform):
    assert frameworks_dir, \
        "Frameworks dir is not specified."
    assert os.path.isdir(frameworks_dir), \
        "{} must be specified.".format(frameworks_dir)
    framework_dir = os.path.join(frameworks_dir, framework)
    assert os.path.isdir(framework_dir), \
        "{} must be specified.".format(framework_dir)
    platform_dir = os.path.join(framework_dir, platform)
    build_script = None
    script = "build.bat" if os.name == "nt" else "build.sh"
    if os.path.isdir(platform_dir):
        script = os.path.join(platform_dir, script)
        if os.path.isfile(script):
            build_script = script
    if build_script is None:
        # Ideally, should check the parent directory until the
        # framework directory. Save this for the future
        build_script = os.path.join(framework_dir, script)
        getLogger().warning("Directory {} ".format(platform_dir) +
                            "doesn't exist. Use " +
                            "{} instead".format(framework_dir))
    assert os.path.isfile(build_script), \
        "Cannot find build script in {} for ".format(framework_dir) + \
        "platform {}".format(platform)
    return build_script
