#!/bin/sh

set -ex

rm -rf $1/build/
$1/scripts/build_local.sh -DBUILD_SHARED_LIBS=OFF -DBUILD_BINARY=ON -DBUILD_SHARE_DIR=ON -DBUILD_OBSERVERS=ON -DUSE_ZSTD=ON -DBLAS=MKL -DUSE_OBSERVERS=ON
cp $1/build/bin/caffe2_benchmark $2
