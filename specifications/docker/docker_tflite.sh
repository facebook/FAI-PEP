#!/bin/bash

set -ex

export MAX_JOBS=1

# install python
apt-get update
apt-get -y install python python-pip git-core

pip install virtualenv

# setup virtualenv
VENV_DIR=/tmp/venv
PYTHON="$(which python)"
if [[ "${CIRCLE_JOB}" =~ py((2|3)\\.?[0-9]?\\.?[0-9]?) ]]; then
    PYTHON=$(which "python${BASH_REMATCH[1]}")
fi
$PYTHON -m virtualenv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install -U pip setuptools

# define some variables
FAI_PEP_DIR=/tmp/FAI-PEP
CONFIG_DIR=/tmp/config
REPO_DIR=/tmp/tensorflow
LOCAL_REPORTER_DIR=/tmp/reporter

BAZEL_DIR=/tmp/bazel
BAZEL=bazel-0.25.0-installer-linux-x86_64.sh

BENCHMARK_FILE=${FAI_PEP_DIR}/specifications/models/tflite/mobilenet_v2/mobilenet_v2_0.35_96.json

mkdir -p "$CONFIG_DIR"
mkdir -p "$LOCAL_REPORTER_DIR"

# clone FAI-PEP
rm -rf ${FAI_PEP_DIR}
git clone https://github.com/facebook/FAI-PEP.git "$FAI_PEP_DIR"
pip install six requests

# set up default arguments
echo "
{
  \"--commit\": \"master\",
  \"--exec_dir\": \"${CONFIG_DIR}/exec\",
  \"--framework\": \"tflite\",
  \"--local_reporter\": \"${CONFIG_DIR}/reporter\",
  \"--model_cache\": \"${CONFIG_DIR}/model_cache\",
  \"--platforms\": \"host\",
  \"--remote_repository\": \"origin\",
  \"--repo\": \"git\",
  \"--repo_dir\": \"${REPO_DIR}\",
  \"--screen_reporter\": null
}
" > ${CONFIG_DIR}/config.txt

# clone/install tflite

apt-get install wget pkg-config g++ zlib1g-dev python zip unzip -y
if [ ! -z ${BAZEL_DIR} ]; then
  mkdir -p ${BAZEL_DIR}
fi
if [ ! -f ${BAZEL_DIR}/${BAZEL} ]; then
  wget -q -O ${BAZEL_DIR}/${BAZEL} https://github.com/bazelbuild/bazel/releases/download/0.25.0/${BAZEL}
fi
chmod +x ${BAZEL_DIR}/${BAZEL}
${BAZEL_DIR}/${BAZEL} --user
export PATH="$PATH:$HOME/bin"

rm -rf ${REPO_DIR}
git clone --recursive --quiet https://github.com/tensorflow/tensorflow.git "$REPO_DIR"

# run benchmark

python ${FAI_PEP_DIR}/benchmarking/run_bench.py -b "${BENCHMARK_FILE}" --config_dir "${CONFIG_DIR}"
