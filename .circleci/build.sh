#!/bin/bash

sh builds/build_pre.sh

case ${TEST_NAME} in
  PYTORCH)
    sh builds/build_pytorch.sh
    ;;
  TFLITE)
    sh builds/build_tflite.sh
    ;;
  *)
    echo "Error, '${TEST_NAME}' not valid mode; Must be one of {PYTORCH, TFLITE}."
    exit 1
    ;;
esac


sh builds/build_post.sh
