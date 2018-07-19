#!/bin/sh

# the configure must be run once beforehand
pushd `pwd`
cd "$1"

# build tensorflow
bazel build --config=opt //tensorflow/tools/pip_package:build_pip_package
rm -rf /tmp/tensorflow_pkg
bazel-bin/tensorflow/tools/pip_package/build_pip_package /tmp/tensorflow_pkg
pip install /tmp/tensorflow_pkg/*.whl

# build benchmark binary
# assuming the configure has set up the NDK and SDK correctly
bazel build -c opt --config=android_arm --cxxopt='--std=c++11' tensorflow/contrib/lite/tools/benchmark:benchmark_model

popd

cp "$1/bazel-bin/tensorflow/contrib/lite/tools/benchmark/benchmark_model" "$2"
