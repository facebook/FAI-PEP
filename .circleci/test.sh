#!/bin/bash

set -ex

source "/tmp/venv/bin/activate"

DIR=$(dirname $0)

# confirm python version
python --version

FRAMEWORK="${CIRCLE_JOB}"
if [[ "${CIRCLE_JOB}" =~ (.*)-py((2|3)\.?[0-9]?\.?[0-9]?) ]]; then
    FRAMEWORK=${BASH_REMATCH[1]}
fi
case ${FRAMEWORK} in
  PYTORCH)
    sh ${DIR}/tests/test_pytorch.sh
    ;;
  TFLITE)
    sh ${DIR}/tests/test_tflite.sh
    ;;
  *)
    echo "Error, '${FRAMEWORK}' not valid mode; Must be one of {PYTORCH, TFLITE}."
    exit 1
    ;;
esac
