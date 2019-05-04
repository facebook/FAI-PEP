#!/bin/sh

set -ex

DIR=${PWD}
# the configure must be run once beforehand
cd "$1"

echo "OS is ${uname}"

LINKER_OPTS=""
if [ "${uname}" = 'Linux' ]; then
  LINKER_OPTS="--linkopt -latomic"
fi
echo "OPTS: ${LINKER_OPTS}"
# build benchmark binary
# assuming the configure has set up the NDK and SDK correctly
bazel build -c opt "${LINKER_OPTS}" \
  tensorflow/lite/tools/benchmark:benchmark_model

cd ${DIR}

cp "$1/bazel-bin/tensorflow/lite/tools/benchmark/benchmark_model" "$2"
