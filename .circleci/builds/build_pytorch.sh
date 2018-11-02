#!/bin/bash

set -ex

pip install numpy pyyaml mkl mkl-include setuptools cmake cffi typing
pip install -c mingfeima mkldnn

PYTORCH_DIR=/tmp/pytorch
git clone --recursive --quiet https://github.com/pytorch/pytorch.git "$PYTORCH_DIR"

# install ninja to speedup the build
pip install ninja
