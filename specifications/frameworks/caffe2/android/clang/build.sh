#!/bin/sh

rm -rf $1/build/
$1/scripts/build_android.sh -DBUILD_BINARY=ON -DBUILD_SHARE_DIR=ON -DBUILD_OBSERVERS=ON -DUSE_ZSTD=ON -DANDROID_TOOLCHAIN=clang
cp $1/build_android/bin/caffe2_benchmark $2
