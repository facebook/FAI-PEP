#!/bin/sh

$1/scripts/build_android.sh -DBUILD_BINARY=ON -DUSE_OBSERVERS=ON -DUSE_ZSTD=ON -DBUILD_SHARE_DIR=ON -DBUILD_OBSERVERS=ON
cp "$1/build_android/bin/caffe2_benchmark" "$2"
