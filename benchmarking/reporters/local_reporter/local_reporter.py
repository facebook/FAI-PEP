#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os

from reporters.reporter_base import ReporterBase
from utils.custom_logger import getLogger
from utils.utilities import getDirectory, getFilename


class LocalReporter(ReporterBase):
    def __init__(self, local_reporter):
        self.local_reporter = local_reporter
        super(LocalReporter, self).__init__()

    def report(self, content):
        data = content[self.DATA]
        if data is None or len(data) == 0:
            getLogger().info("No data to write")
            return
        meta = content[self.META]
        net_name = meta["net_name"]
        netdir = getFilename(net_name)
        platform_name = meta[self.PLATFORM]
        platformdir = getFilename(platform_name)
        framework_name = meta["framework"]
        frameworkdir = getFilename(framework_name)
        metric_name = meta["metric"]
        metric_dir = getFilename(metric_name)
        id_dir = getFilename(meta["identifier"])
        ts = float(meta["commit_time"])
        commit = meta["commit"]
        datedir = getDirectory(commit, ts)
        dirname = os.path.join(
            self.local_reporter,
            platformdir,
            frameworkdir,
            netdir,
            metric_dir,
            id_dir,
            datedir,
        )
        i = 0
        while os.path.exists(os.path.join(dirname, str(i))):
            i = i + 1
        dirname = os.path.join(dirname, str(i))
        os.makedirs(dirname)
        for d in data:
            filename = os.path.join(dirname, getFilename(d) + ".txt")
            content_d = json.dumps(data[d], indent=2, sort_keys=True)
            with open(filename, "w") as file:
                file.write(content_d)
        filename = os.path.join(dirname, getFilename(self.META) + ".txt")
        with open(filename, "w") as file:
            content_meta = json.dumps(meta, indent=2, sort_keys=True)
            file.write(content_meta)
        pname = platform_name
        if "platform_hash" in meta:
            pname = pname + " ({})".format(meta["platform_hash"])
        getLogger().info("Writing file for {}: {}".format(pname, dirname))
