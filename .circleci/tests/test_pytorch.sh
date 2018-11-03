#!/bin/bash

set -ex

# source /tmp/venv/bin/activate
sudo pip install requests

CONFIG_DIR=/tmp/config/pytorch
PYTORCH_DIR=/tmp/pytorch
LOCAL_REPORTER_DIR=/tmp/reporter/pytorch

mkdir -p "$CONFIG_DIR"
mkdir -p "$LOCAL_REPORTER_DIR"
echo "{}" > "$CONFIG_DIR/config.txt"

cd /tmp/FAI-PEP
python ./benchmarking/run_bench.py -b specifications/models/caffe2/squeezenet/squeezenet.json -remote_repository origin --repo_dir "$PYTORCH_DIR" --platforms host --repo git --commit master --framework caffe2 --screen_reporter  --local_reporter "${LOCAL_REPORTER_DIR}"  --config_dir "${CONFIG_DIR}" --exec_dir "${CONFIG_DIR}/exec"
