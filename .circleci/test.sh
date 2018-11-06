#!/bin/bash

set -ex

source "/tmp/venv/bin/activate"

DIR=$(dirname $0)

case ${CIRCLE_JOB} in
  PYTORCH)
    sh ${DIR}/tests/test_pytorch.sh
    ;;
  TFLITE)
    sh ${DIR}/tests/test_tflite.sh
    ;;
  *)
    echo "Error, '${CIRCLE_JOB}' not valid mode; Must be one of {PYTORCH, TFLITE}."
    exit 1
    ;;
esac
