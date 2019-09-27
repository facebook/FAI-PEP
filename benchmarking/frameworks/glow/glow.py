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
        return cmds

    def runOnPlatform(self, total_num, cmd, platform, platform_args,
            converter):
        output, meta = platform.runBenchmark(cmd, platform_args=platform_args)
        results = {}
        self._maybeAddJsonOutput(output, results)
        self._maybeAddTraceOutput(platform, results)
        results["meta"] = meta
        return results

    def _maybeAddJsonOutput(self, output, results):
        if output is None:
            return False
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

    def _maybeAddTraceOutput(self, platform, results):
        traceFile = os.path.join(platform.getOutputDir(), "trace")
        if not os.path.exists(traceFile):
            return
        with open(traceFile, 'r') as fp:
            line = fp.readline()
            while line:
                try:
                    parsed = json.loads(line.rstrip(", \n\t"))
                    key = "NET " + parsed["name"]
                    if key in results.keys():
                        results[key]["values"].append(parsed["dur"])
                    else:
                        results[key] = {
                            "type": "NET",
                            "metric": parsed["name"],
                            "unit": "microsecond",
                            "values": [parsed["dur"]]
                        }
                except json.JSONDecodeError:
                    pass
                except KeyError:
                    pass
                line = fp.readline()
