#!/bin/bash

DIR=$(dirname $0)

export MAX_JOBS=8

# setup sccache wrappers
if hash sccache 2>/dev/null; then
    SCCACHE_BIN_DIR="/tmp/sccache"
    mkdir -p "$SCCACHE_BIN_DIR"
    for compiler in cc c++ gcc g++ x86_64-linux-gnu-gcc; do
        (
            echo "#!/bin/sh"
            echo "exec $(which sccache) $(which $compiler) \"\$@\""
        ) > "$SCCACHE_BIN_DIR/$compiler"
        chmod +x "$SCCACHE_BIN_DIR/$compiler"
    done
    export PATH="$SCCACHE_BIN_DIR:$PATH"
fi

# setup virtualenv
VENV_DIR=/tmp/venv
PYTHON="$(which python)"
if [[ "${CIRCLE_JOB}" =~ py((2|3)\\.?[0-9]?\\.?[0-9]?) ]]; then
    PYTHON=$(which "python${BASH_REMATCH[1]}")
fi
# $PYTHON -m virtualenv "$VENV_DIR"
# source "$VENV_DIR/bin/activate"
pip install -U pip setuptools

# clone FAI-PEP
FAI_PEP_DIR=/tmp/FAI-PEP
rm -rf ${FAI_PEP_DIR}
git clone https://github.com/facebook/FAI-PEP.git "$FAI_PEP_DIR"

pip install six requests

mkdir

case ${TEST_NAME} in
  PYTORCH)
    sudo pip install numpy pyyaml mkl mkl-include setuptools cmake cffi typing

    PYTORCH_DIR=/tmp/pytorch
    rm -rf ${PYTORCH_DIR}
    git clone --recursive --quiet https://github.com/pytorch/pytorch.git "$PYTORCH_DIR"

    # install ninja to speedup the build
    sudo pip install ninja
    ;;
  TFLITE)
    TFLITE_DIR=/tmp/tensorflow
    rm -rf ${TFLITE_DIR}
    git clone --recursive --quiet https://github.com/tensorflow/tensorflow.git "$TFLITE_DIR"
    ;;
  *)
    echo "Error, '${TEST_NAME}' not valid mode; Must be one of {PYTORCH, TFLITE}."
    exit 1
    ;;
esac


# report sccache hit/miss stats
if hash sccache 2>/dev/null; then
    sccache --show-stats
fi
