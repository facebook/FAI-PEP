#!/bin/bash

set -ex

export PATH="$PATH:$HOME/bin"
CONFIG_DIR=/tmp/config
LOCAL_REPORTER_DIR=/tmp/reporter
TENSORFLOW_DIR=/tmp/tensorflow

python /tmp/FAI-PEP/benchmarking/run_bench.py -b specifications/models/tflite/mobilenet_v2/mobilenet_v2_1.0_224.json -remote_repository origin --repo_dir "${TENSORFLOW_DIR}" --platforms host --repo git --commit master --framework tflite --screen_reporter  --local_reporter "${LOCAL_REPORTER_DIR}" --config_dir "${CONFIG_DIR}" --exec_dir "${CONFIG_DIR}/exec"
