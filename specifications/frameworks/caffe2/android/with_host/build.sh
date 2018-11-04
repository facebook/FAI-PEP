#!/bin/sh

set -ex

DIR=$(dirname "$2")

$1/scripts/build_local.sh -DBUILD_SHARED_LIBS=OFF -DBUILD_BINARY=ON -DBUILD_SHARE_DIR=ON -DBUILD_OBSERVERS=ON -DUSE_ZSTD=ON -DUSE_OBSERVERS=ON -DUSE_OPENCV=ON
$1/scripts/build_android.sh -DBUILD_BINARY=ON -DUSE_OBSERVERS=ON -DUSE_ZSTD=ON -DBUILD_SHARE_DIR=ON -DBUILD_OBSERVERS=ON
cp "$1/build/bin/convert_image_to_tensor" "${DIR}/convert_image_to_tensor"
cp "$1/build_android/bin/caffe2_benchmark" "$2"
