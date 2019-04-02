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

import hashlib
import json
import os
import datetime

from bridge.file_storages import UploadDownloadFiles
from utils.custom_logger import getLogger


class FileHandler(object):
    def __init__(self, args):
        self.config_filename = args.cache_config
        self.root_dir = args.root_model_dir
        self.file_storage = UploadDownloadFiles(args)
        self.config = None
        if not os.path.isfile(self.config_filename):
            self.config = {}
        else:
            with open(self.config_filename, 'r') as f:
                try:
                    self.config = json.load(f)
                except Exception:
                    self.config = {}
        self._updateConfig()

    def uploadFile(self, f, md5, basefilename, cache_file):
        if f.startswith("https://") or f.startswith("http://"):
            return f, md5
        if f.startswith("//"):
            assert self.root_dir, \
                "root_dir must be specified for relative path"
            path = self.root_dir + f[1:]
        elif f.startswith("/"):
            path = f
        else:
            path = os.path.dirname(os.path.realpath(basefilename)) + "/" + f

        if not os.path.isfile(path):
            return f, md5

        upload_path, cached_md5 = self._getCachedFile(path)
        filename = os.path.basename(f)
        if upload_path is None or not cache_file or md5 is not cached_md5:
            upload_path = self.file_storage.upload(orig_path=f,
                                                   file=path,
                                                   permanent=False)
            if cache_file or md5 is not cached_md5:
                md5 = self._saveCachedFile(path, upload_path)
        else:
            getLogger().info("File {} cached, skip uploading".format(filename))
        return upload_path, md5

    def _getCachedFile(self, path):
        md5 = None
        if path in self.config:
            entry = self.config[path]
            if os.path.isfile(path):
                md5 = self._calculateMD5(path)
            if entry["md5"] == md5:
                return entry["upload_path"], md5
        return None, md5

    def _saveCachedFile(self, path, upload_path):
        calculate_md5 = self._calculateMD5(path)
        entry = {
            "local_path": path,
            "md5": calculate_md5,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "upload_path": upload_path
        }
        self.config[path] = entry
        self._updateConfigFile()
        return calculate_md5

    def _calculateMD5(self, filename):
        m = hashlib.md5()
        m.update(open(filename, 'rb').read())
        md5 = m.hexdigest()
        return md5

    def _updateConfigFile(self):
        json_file = json.dumps(self.config, indent=2, sort_keys=True)
        with open(self.config_filename, 'w') as f:
            f.write(json_file)

    def _updateConfig(self):
        cutoff_time = datetime.datetime.now() - datetime.timedelta(days=21)
        # Delete files that are three weeks old
        updated = False
        keys = list(self.config.keys())
        for path in keys:
            entry = self.config[path]
            t = datetime.datetime.strptime(entry["time"], "%Y-%m-%d %H:%M:%S")
            if t < cutoff_time:
                updated = True
                del self.config[path]
        if updated:
            self._updateConfigFile()
