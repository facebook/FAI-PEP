#!/bin/sh

set -ex

DIR=${PWD}
# the configure must be run once beforehand
cd "$1"
unamestr=`uname`
echo "OS is $unamestr"
LINKER_OPTS=""
if [ "$unamestr" == "Linux" ]; then
  LINKER_OPTS="--linkopt -latomic"
fi
# build benchmark binary
# assuming the configure has set up the NDK and SDK correctly
bazel build -c opt ${LINKER_OPTS} \
  tensorflow/lite/tools/benchmark:benchmark_model

cd ${DIR}

cp "$1/bazel-bin/tensorflow/lite/tools/benchmark/benchmark_model" "$2"
