#!/bin/bash

case ${TEST_NAME} in
  PYTORCH)
    sh tests/test_pytorch.sh
    ;;
  TFLITE)
    sh tests/test_tflite.sh
    ;;
  *)
    echo "Error, '${TEST_NAME}' not valid mode; Must be one of {PYTORCH, TFLITE}."
    exit 1
    ;;
esac
