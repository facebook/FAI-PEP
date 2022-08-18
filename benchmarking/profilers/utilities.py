#!/usr/bin/env python

##############################################################################
# Copyright 2021-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import os
from typing import Dict, Mapping
from uuid import uuid4

from bridge.file_storage.upload_files.file_uploader import FileUploader
from utils.custom_logger import getLogger


def generate_perf_filename(model_name="benchmark", hash=None):
    """Given the provided model name and optional hash, generate a unique base filename."""
    unique_name = os.getenv("JOB_IDENTIFIER", None)
    if unique_name is None:
        unique_name = uuid4()
    elif hash is None:
        hash = os.getenv("JOB_ID", None)
    if hash is not None:
        unique_name += f"_{hash}"
    return f"{model_name}_perf_{unique_name}"


def upload_profiling_reports(files: Mapping[str, str]) -> Dict:
    """
    Upload to aibench profiling reports.
    Accepts dict of key -> local file path, uploads using file basename
    and returns meta dict of key -> url.
    """
    meta = {}
    profiling_reports_uploader = FileUploader("profiling_reports").get_uploader()
    for key, file in files.items():
        if not os.path.isfile(file):
            raise FileNotFoundError(f"File {file} does not exist.")
        try:
            url = profiling_reports_uploader.upload_file(file)
            meta.update({key: url})
        except Exception as e:
            getLogger().exception(
                f"Warning: could not upload {key}: {file}. Skipping.\nException: {e}"
            )
    return meta


def upload_output_files(files: Mapping[str, str]) -> Dict:
    """
    Upload to aibench profiling reports.
    Accepts dict of key -> local file path, uploads using file basename
    and returns meta dict of key -> url.
    """
    meta = {}
    profiling_reports_uploader = FileUploader("output_files").get_uploader()
    for key, file in files.items():
        if not os.path.isfile(file):
            raise FileNotFoundError(f"File {file} does not exist.")
        try:
            url = profiling_reports_uploader.upload_file(file)
            meta.update({key: url})
        except Exception:
            getLogger().exception(f"Warning: could not upload {key}: {file}. Skipping.")
    return meta
