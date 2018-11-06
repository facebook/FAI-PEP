#!/bin/bash

set -ex

pip install numpy pyyaml mkl mkl-include setuptools cmake cffi typing

REPO_DIR=/tmp/pytorch

rm -rf ${REPO_DIR}
git clone --recursive --quiet https://github.com/pytorch/pytorch.git "$REPO_DIR"

# install ninja to speedup the build
pip install ninja
