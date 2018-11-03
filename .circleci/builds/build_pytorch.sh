#!/bin/bash

set -ex

pip install numpy pyyaml mkl mkl-include setuptools cmake cffi typing

PYTORCH_DIR=/tmp/pytorch
rm -rf ${PYTORCH_DIR}
git clone --recursive --quiet https://github.com/pytorch/pytorch.git "$PYTORCH_DIR"

# install ninja to speedup the build
pip install ninja
