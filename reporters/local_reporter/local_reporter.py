#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from reporters.reporter_base import ReporterBase
from utils.arg_parse import getParser, getArgs
from utils.custom_logger import getLogger
from utils.utilities import getDirectory

import json
import os

getParser().add_argument("--local_reporter",
    help="Save the result to a directory specified by this argument.")


class LocalReporter(ReporterBase):
    def __init__(self):
        super(LocalReporter, self).__init__()

    def report(self, content):
        data = content[self.DATA]
        if data is None or len(data) == 0:
            getLogger().info("No data to write")
            return  
        net_name = content[self.META]['net_name']
        netdir = self._getFilename(net_name) + "/"
        platform_name = content[self.META][self.PLATFORM]
        platformdir = self._getFilename(platform_name) + "/"
        metric_name = content[self.META]['metric']
        metric_dir = self._getFilename(metric_name) + "/"
        id_dir = self._getFilename(getArgs().identifier) + "/"
        ts = float(content[self.META]['commit_time'])
        commit = content[self.META]['commit']
        datedir = getDirectory(commit, ts)
        dirname = platformdir + netdir + metric_dir + id_dir + datedir
        dirname = getArgs().local_reporter + "/" + dirname
        i = 0
        while os.path.exists(dirname + str(i)):
            i = i+1
        dirname = dirname + str(i) + "/"
        os.makedirs(dirname)
        for d in data:
            filename = dirname + self._getFilename(d) + ".txt"
            content_d = json.dumps(data[d])
            with open(filename, 'w') as file:
                file.write(content_d)
        filename = dirname + self._getFilename(self.META) + ".txt"
        with open(filename, 'w') as file:
            content_meta = json.dumps(content[self.META])
            file.write(content_meta)
        getLogger().info("Writing file: %s" % dirname)

    def _getFilename(self, name):
        filename = name.replace(' ', '-').replace('/', '-')
        return "".join([c for c in filename
                        if c.isalpha() or c.isdigit() or
                        c == '_' or c == '.' or c == '-']).rstrip()
