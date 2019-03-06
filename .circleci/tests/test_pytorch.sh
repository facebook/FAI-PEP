#!/bin/bash

set -ex

CONFIG_DIR=/tmp/config
IMAGENET_DIR=/tmp/imagenet
LOCAL_REPORTER_DIR=/tmp/reporter
MODEL_DIR=/tmp/model/group4
REPO_DIR=/tmp/pytorch
REPO=caffe2

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
  \"--root_model_dir\": \"${CONFIG_DIR}/root_model_dir\",
  \"--screen_reporter\": null
}
" > ${CONFIG_DIR}/config.txt

# test squeezenet
python benchmarking/run_bench.py -b specifications/models/caffe2/squeezenet/squeezenet.json --user_string "CI Test" --config_dir "${CONFIG_DIR}"

# test shufflenet on imagenet
wget -O /tmp/shufflenet.tar.gz https://s3.amazonaws.com/download.caffe2.ai/models/shufflenet/new_shufflenet/shufflenet.tar.gz
tar -xzvf /tmp/shufflenet.tar.gz -C /tmp

wget -O /tmp/imagenet.tar.gz https://s3.amazonaws.com/download.caffe2.ai/models/imagenet/imagenet.tar.gz
tar -xzvf /tmp/imagenet.tar.gz -C /tmp

python benchmarking/run_bench.py -b specifications/models/caffe2/shufflenet/shufflenet_accuracy_imagenet_simple.json --string_map "{\"IMAGENET_DIR\": \"${IMAGENET_DIR}\", \"MODEL_DIR\": \"${MODEL_DIR}\"}" --user_string "CI Test" --config_dir "${CONFIG_DIR}"
