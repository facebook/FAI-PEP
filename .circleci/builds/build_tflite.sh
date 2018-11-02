#!/bin/bash

set -ex

TFLITE_DIR=/tmp/pytorch
git clone --recursive --quiet https://github.com/tensorflow/tensorflow.git "$TFLITE_DIR"
