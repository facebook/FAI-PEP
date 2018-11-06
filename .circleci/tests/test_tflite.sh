#!/bin/bash

set -ex

export PATH="$PATH:$HOME/bin"

FAI_PEP_DIR=/tmp/FAI-PEP
CONFIG_DIR=/tmp/config
LOCAL_REPORTER_DIR=/tmp/reporter
REPO_DIR=/tmp/tensorflow
REPO=tflite

mkdir -p "$CONFIG_DIR"
mkdir -p "$LOCAL_REPORTER_DIR"

echo "
{
  \"--commit\": \"master\",
  \"--exec_dir\": \"${CONFIG_DIR}/exec\",
  \"--framework\": \"${REPO}\",
  \"--local_reporter\": \"${CONFIG_DIR}/reporter\",
  \"--model_cache\": \"${CONFIG_DIR}/model_cache\",
  \"--platforms\": \"host\",
  \"--remote_repository\": \"origin\",
  \"--repo\": \"git\",
  \"--repo_dir\": \"${REPO_DIR}\",
  \"--screen_reporter\": null
}
" > ${CONFIG_DIR}/config.txt

python ${FAI_PEP_DIR}/benchmarking/run_bench.py -b ${FAI_PEP_DIR}/specifications/models/tflite/mobilenet_v2/mobilenet_v2_0.35_96.json --config_dir "${CONFIG_DIR}"
