#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from reporters.reporter_base import ReporterBase
from utils.arg_parse import getArgs
from utils.custom_logger import getLogger
from utils.utilities import getFilename

import json
import os


class SimpleLocalReporter(ReporterBase):
    def __init__(self):
        super(SimpleLocalReporter, self).__init__()

    def report(self, content):
        data = content[self.DATA]
        if data is None or len(data) == 0:
            getLogger().info("No data to write")
            return
        meta = content[self.META]
        id_dir = getFilename(meta["identifier"]) + "/"
        dirname = id_dir
        dirname = getArgs().simple_local_reporter + "/" + dirname
        assert not os.path.exists(dirname), \
            "Simple local reporter should not have multiple entries"
        os.makedirs(dirname)
        with open(dirname + "/data.txt", 'w') as file:
            content_d = json.dumps(data)
            file.write(content_d)
        platform_name = meta[self.PLATFORM]
        pname = platform_name
        if "platform_hash" in meta:
            pname = pname + " ({})".format(meta["platform_hash"])
        getLogger().info("Writing file for {}: {}".format(pname, dirname))
