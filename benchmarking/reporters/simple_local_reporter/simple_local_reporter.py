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

import json
import os
import shutil
import tempfile

from reporters.reporter_base import ReporterBase
from utils.custom_logger import getLogger
from utils.utilities import getFilename


class SimpleLocalReporter(ReporterBase):
    def __init__(self, simple_local_reporter):
        self.simple_local_reporter = simple_local_reporter
        super(SimpleLocalReporter, self).__init__()

    def report(self, content):
        data = content[self.DATA]
        if data is None or len(data) == 0:
            getLogger().info("No data to write")
            return
        meta = content[self.META]

        dirname = None
        if "identifier" in meta:
            id_dir = getFilename(meta["identifier"])
            dirname = os.path.join(self.simple_local_reporter, id_dir)
        else:
            dirname = tempfile.mkdtemp(dir=self.simple_local_reporter, prefix="aibench")

        if os.path.exists(dirname):
            shutil.rmtree(dirname, True)
        os.makedirs(dirname)
        with open(os.path.join(dirname, "data.txt"), "w") as file:
            content_d = json.dumps(data)
            file.write(content_d)
        pname = meta[self.PLATFORM]
        if "platform_hash" in meta:
            pname = pname + " ({})".format(meta["platform_hash"])
        getLogger().info("Writing file for {}: {}".format(pname, dirname))
