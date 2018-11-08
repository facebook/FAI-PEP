
# Experiment with docker

Even if you don't have any prior experience with FAI-PEP, you can try it out with all the necessary steps with a container. We have set up scripts to perform the benchmark end to end, from setting up environment, installing prerequisites in the script, to building frameworks and performing the benchmarks by launching FAI-PEP.

The docker image performs benchmarking on the host system. Benchmarking on android or ios phones are more complicated and is not described in this page.

Below you will see how the end-to-end experience looks like for both *tflite* and *caffe2*.

### TFLite
The script to perform benchmark end-to-end can be found [here](https://github.com/facebook/FAI-PEP/blob/master/specifications/docker/docker_tflite.sh).

```
git clone git@github.com:facebook/FAI-PEP.git
docker pull ubuntu:16.04
pid=$(docker run -t -d ubuntu:16.04)
docker cp FAI-PEP/specifications/docker/docker_tflite.sh `echo ${pid}`:/tmp/docker_tflite.sh
docker exec `echo ${pid}` /tmp/docker_tflite.sh
```

### Caffe2
The script to benchmark caffe2 can be found [here](https://github.com/facebook/FAI-PEP/blob/master/specifications/docker/docker_pytorch.sh). It is more complicated, as it includes a test that benchmarks the both the accuracy and performance on the imagenet validation dataset.

In order to do that, you need to map the local imagenet directory to a directory in the docker `-v <local imagenet directory>:/tmp/imagenet`. Then the script takes over the rest.

If you want to try out the benchmark on imagenet dataset, when invoking script `/tmp/docker_pytorch.sh`, add argument `/tmp/imagenet`. If you just want to try out the plain benchmarking, run it without the argument.
```
git clone git@github.com:facebook/FAI-PEP.git
docker pull ubuntu:16.04
pid=$(docker run -t -d -v <local imagenet directory>:/tmp/imagenet ubuntu:16.04)
docker cp FAI-PEP/specifications/docker/docker_pytorch.sh `echo ${pid}`:/tmp/docker_pytorch.sh
docker exec `echo ${pid}` /tmp/docker_pytorch.sh /tmp/imagenet
```
