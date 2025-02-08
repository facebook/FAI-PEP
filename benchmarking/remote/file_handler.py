#!/usr/bin/env python

# pyre-unsafe

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


import datetime
import hashlib
import json
import os
import tempfile

import pkg_resources
from bridge.file_storages import UploadDownloadFiles
from utils.custom_logger import getLogger


class FileHandler:
    def __init__(self, args):
        self.config_filename = args.cache_config
        self.root_dir = args.root_model_dir
        self.file_storage = UploadDownloadFiles(args)
        self.config = None
        if not os.path.isfile(self.config_filename):
            self.config = {}
        else:
            with open(self.config_filename) as f:
                try:
                    self.config = json.load(f)
                except Exception:
                    self.config = {}
        self._updateConfig()

    def uploadFile(self, filename, md5, basefilename, cache_file):
        if filename.startswith("https://") or filename.startswith("http://"):
            return filename, md5
        if filename.startswith("specifications"):
            """We will handle the spcical case here that the file is from
            internal binary. We will first load it, save it as a temp file, and
            then return the temp path. In general, we don't encourage this case.
            """
            if not pkg_resources.resource_exists("aibench", filename):
                getLogger().error(f"Cannot find {filename}")
            raw_context = pkg_resources.resource_string("aibench", filename)
            temp_name = filename.split("/")[-1]
            temp_dir = tempfile.mkdtemp(prefix="aibench")
            path = os.path.join(temp_dir, temp_name)
            with open(path, "w") as f:
                f.write(raw_context.decode("utf-8"))
        elif filename.startswith("//"):
            assert self.root_dir, "root_dir must be specified for relative path"
            path = self.root_dir + filename[1:]
        elif filename.startswith("/"):
            path = filename
        else:
            path = os.path.join(
                os.path.dirname(os.path.realpath(basefilename)), filename
            )

        if not os.path.isfile(path) or filename.startswith("//manifold"):
            getLogger().info(f"Skip uploading {filename}")
            return filename, md5

        upload_path, cached_md5 = self._getCachedFile(path)
        base_filename = os.path.basename(filename)
        if upload_path is None or not cache_file or md5 is not cached_md5:
            upload_path = self.file_storage.upload(
                orig_path=filename, file=path, permanent=False
            )
            if cache_file or md5 is not cached_md5:
                md5 = self._saveCachedFile(path, upload_path)
        else:
            getLogger().info(f"File {base_filename} cached, skip uploading")
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
            "upload_path": upload_path,
        }
        self.config[path] = entry
        self._updateConfigFile()
        return calculate_md5

    def _calculateMD5(self, filename):
        m = hashlib.md5()
        with open(filename, "rb") as f:
            m.update(f.read())
        md5 = m.hexdigest()
        return md5

    def _updateConfigFile(self):
        json_file = json.dumps(self.config, indent=2, sort_keys=True)
        with open(self.config_filename, "w") as f:
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
