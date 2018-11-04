#!/bin/bash

set -ex

FAI_PEP=/tmp/FAI-PEP
CONFIG_DIR=/tmp/config
PYTORCH_DIR=/tmp/pytorch
LOCAL_REPORTER_DIR=/tmp/reporter

python ${FAI_PEP}/benchmarking/run_bench.py -b ${FAI_PEP}/specifications/models/caffe2/squeezenet/squeezenet.json -remote_repository origin --repo_dir "$PYTORCH_DIR" --platforms host --repo git --commit master --framework caffe2 --screen_reporter  --local_reporter "${LOCAL_REPORTER_DIR}"  --config_dir "${CONFIG_DIR}" --exec_dir "${CONFIG_DIR}/exec" --model_cache "${CONFIG_DIR}/model_cache"
