#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import os

from .custom_logger import getLogger
from .subprocess_with_logger import processRun


def buildProgramPlatform(dst, repo_dir, framework, frameworks_dir, platform):
    script = _getBuildScript(framework, frameworks_dir, platform)
    dst_dir = os.path.dirname(dst)
    if os.path.isfile(dst):
        os.remove(dst)
    elif not os.path.isdir(dst_dir):
        os.makedirs(dst_dir)

    result = processRun(['sh', script, repo_dir, dst])[0]
    if result is not None:
        os.chmod(dst, 0o777)
    print(result)

    if not os.path.isfile(dst):
        getLogger().error(
            "Build program using script {} failed.".format(script))
        return False
    return True


def _getBuildScript(framework, frameworks_dir, platform):
    assert frameworks_dir, \
        "Frameworks dir is not specified."
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
        getLogger().warning("Directory {} ".format(platform_dir) +
                            "doesn't exist. Use " +
                            "{} instead".format(framework_dir))
    assert os.path.isfile(build_script), \
        "Cannot find build script in {} for ".framework_dir + \
        "platform {}".format(platform)
    return build_script
