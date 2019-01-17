#!/bin/bash

set -ex
sudo apt-get -y install wget zip unzip

pip install numpy pyyaml mkl mkl-include setuptools cmake cffi typing

REPO_DIR=/tmp/pytorch

rm -rf ${REPO_DIR}
git clone --recursive --quiet https://github.com/pytorch/pytorch.git "$REPO_DIR"

# install ninja to speedup the build
pip install ninja

wget -O /tmp/opencv.zip https://github.com/opencv/opencv/archive/3.4.3.zip
unzip -q /tmp/opencv.zip -d /tmp/
cd /tmp/opencv-3.4.3/
mkdir build
cd build
cmake ..
make -j 1
sudo make install
