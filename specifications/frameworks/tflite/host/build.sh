#!/bin/sh

DIR=${PWD}
# the configure must be run once beforehand
cd "$1"

LINKER_OPTS=""
if [[ "$OSTYPE" == "linux-gnu" ]]; then
  LINKER_OPTS="--linkopt -latomic"
fi
# build benchmark binary
# assuming the configure has set up the NDK and SDK correctly
bazel build -c opt ${LINKER_OPTS} \
  tensorflow/lite/tools/benchmark:benchmark_model

cd ${DIR}

cp "$1/bazel-bin/tensorflow/lite/tools/benchmark/benchmark_model" "$2"
