#!/bin/sh

# the configure must be run once beforehand
cd "$1"

# build benchmark binary
# assuming the configure has set up the NDK and SDK correctly
bazel build -c opt \
  --config=android_arm \
  --cxxopt='--std=c++11' \
  tensorflow/contrib/lite/tools/benchmark:benchmark_model

cp "$1/bazel-bin/tensorflow/contrib/lite/tools/benchmark/benchmark_model" "$2"
