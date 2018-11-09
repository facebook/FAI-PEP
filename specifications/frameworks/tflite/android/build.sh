#!/bin/sh

set -ex

DIR=${PWD}
# the configure must be run once beforehand
cd "$1"

# build benchmark binary
# assuming the configure has set up the NDK and SDK correctly
bazel build -c opt \
  --config=android_arm \
  --cxxopt='--std=c++11' \
  tensorflow/lite/tools/benchmark:benchmark_model

cd ${DIR}

cp "$1/bazel-bin/tensorflow/lite/tools/benchmark/benchmark_model" "$2"
