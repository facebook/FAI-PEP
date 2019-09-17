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
import json
from six import string_types
from frameworks.framework_base import FrameworkBase


class GlowFramework(FrameworkBase):
    def __init__(self, tempdir, args):
        super(GlowFramework, self).__init__(args)
        self.tempdir = os.path.join(tempdir, self.getName())
        os.makedirs(self.tempdir, 0o777)

    def getName(self):
        return "glow"

    def runBenchmark(self, info, benchmark, platform):
        output, output_files = \
            super(GlowFramework, self).runBenchmark(info, benchmark,
                                                      platform)
        return output, output_files

    def composeRunCommand(self, commands, platform, programs,
                          model, test, model_files,
                          input_files, output_files, shared_libs,
                          preprocess_files=None, main_command=False):
        cmds = super(GlowFramework, self).composeRunCommand(commands, platform,
                programs, model, test, model_files, input_files, output_files,
                shared_libs, preprocess_files, main_command)
        if cmds:
            return cmds

        cmd = ["--net", model_files["predict"],
               "--iter", test["iter"]
               ]
        if "program" in programs:
            cmd = [programs["program"]] + cmd
        if "init" in model_files:
            cmd.append("--init_net")
            cmd.append(model_files["init"])
        if "commands" in test:
            if "glow" in test["commands"]:
                for key in test["commands"]["glow"]:
                    val = test["commands"]["glow"][key]
                    cmd.extend(["--" + key, val])

        if shared_libs:
            cmd = ["export", "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:"
                    + os.path.dirname(shared_libs[0]), "&&"] + cmd
        cmd = ' '.join(str(s) for s in cmd)
        return [cmd]

    def runOnPlatform(self, total_num, cmd, platform, platform_args,
            converter):
        output, meta = platform.runBenchmark(cmd, platform_args=platform_args)
        result = self._collectData(output)
        result["meta"] = meta
        return result

    def _collectData(self, output):
        if output is None:
            return False
        results = {}
        rows = output
        if isinstance(output, string_types):
            rows = output.split('\n')
        i = 0
        while i < len(rows):
            try:
                parsed = json.loads(rows[i])
                results[parsed["type"] + " " + parsed["metric"]] = parsed
            except json.JSONDecodeError:
                pass
            i += 1
        return results
