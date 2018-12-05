#!/bin/bash

set -ex

export MAX_JOBS=8
DIR=$(dirname $0)

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
PYTHON_SUFFIX="2"
FRAMEWORK="${CIRCLE_JOB}"
if [[ "${CIRCLE_JOB}" =~ (.*)-py((2|3)\.?[0-9]?\.?[0-9]?) ]]; then
    PYTHON=$(which "python${BASH_REMATCH[2]}")
    PYTHON_SUFFIX=${BASH_REMATCH[2]}
    FRAMEWORK=${BASH_REMATCH[1]}
fi

if [ ${PYTHON_SUFFIX} != "2" ]; then
    sudo apt-get update
    sudo apt-get -y install "python${PYTHON_SUFFIX}-pip"
    pip${PYTHON_SUFFIX} install virtualenv
fi

$PYTHON -m virtualenv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install -U pip setuptools

sudo apt-get update

# confirm python version
python --version

pip install six requests

case ${FRAMEWORK} in
  PYTORCH)
    sh ${DIR}/builds/build_pytorch.sh
    ;;
  TFLITE)
    sh ${DIR}/builds/build_tflite.sh
    ;;
  *)
    echo "Error, '${FRAMEWORK}' not valid mode; Must be one of {PYTORCH, TFLITE}."
    exit 1
    ;;
esac


# report sccache hit/miss stats
if hash sccache 2>/dev/null; then
    sccache --show-stats
fi
