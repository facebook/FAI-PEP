# ML Benchmark Platform

The ML benchmark platform a framework and backend agnostic benchmarking platform to compare machine learning inferencing runtime information of a set of models on a variety of backends. It also provides a means to check performance regressions on each commit.

Currently two performance metrics are collected:

* delay : the delay of running the entire network and/or the delay of running each individual operator.
* error : the error between the values of the outputs running a model and the golden outputs.

## Framework and backend agnostic benchmarking platforms

Machine learning is a rapidly evolving area with many moving parts: new and existing framework enhancement, new hardware solutions, new software backends, and new models. With so many moving parts, it is very difficult to quickly evaluating the performance of a machine learning model. However, such evaluation is vastly important in guiding resource allocation in:

* the development of the frameworks
* the optimization of the software backends
* the selection of the hardware solutions
* the iteration of the machine learning models

This project tries to achieve the following two goals:

* When a new model is added, get the runtime performance of this model on all existing backends easily.
* When a new backend is added, get the runtime performance of all existing models on this backend easily.

The flow of benchmarking is illustrated in the following figure:

![Benchmarking flow](/flow.png)

The flow is composed of three parts:

* A centralized model/benchmark specification
 * A fair input to the comparison
* A centralized benchmark driver with distributed benchmarking execution
 * The same code base for all backends to reduce variation
 * Distributed execution due to the unique build/run environment for each backend
* A centralized data consumption
 * One stop to compare the performance

The currently supported frameworks are: Caffe2
The currently supported model formats are: Caffe2
The currently supported hardware backends: CPU, GPU, Android, linux based systems
The currently supported software backends: Eigen, MKL, NNPACK, OpenGL, CUDA

## Performance regression detection

The benchmark platform also provides a means to compare performance between commits and detect regressions. It uses an A/B testing methodology that compares the runtime difference between a newer commit (treatment) and an older commit (control). What matters is the relative performance between the commits, as the backend platform's condition may be different at different times. Running the same tests on two different commit points at the same time removes most of the variations of the backend. This method has shown to improve the precision of detecting performance regressions.

## Directory structure

The benchmarking codebase resides in `benchmarking` directory. Inside, the `frameworks` directory contains all supported ML frameworks. Add a new framework by creating a new directory, derive from `framework_base.py` and implement all its methods. The `platforms` directory contains all supported ML backend platforms. Add a new backend by creating a new directory, derive from `platform_base.py` and implement all its methods.

The model specifications resides in `specifications` directory. Inside, the `models` directory contains all model and benchmarking specifications organized in model format. The `benchmarks` directory contains a sequence of benchmarks organized in model format. The `frameworks` directory contains custom build scripts for each framework.

## Model/Benchmark specification
The models and benchmarks are specified in json format. It is best to use the example in `/specifications/models/caffe2/squeezenet/squeezenet.json` as an example to understand what data is specified.

A few key items in the specifications

* The models are hosted in third party storage. The download links and their MD5 hashes are specified. The benchmarking tool automatically downloads the model if not found in the local model cache. The MD5 hash of the cached model is computed and compared with the specified one. If they do not match, the model is downloaded again and the MD5 hash is recomputed. This way, if the model is changed, only need to update the specification and the new model is downloaded automatically.
* In the `inputs` field of `tests`, one may specify multiple shapes. This is a short hand to indicate that we benchmark the tests of all shapes in sequence.
* In some field, such as `identifier`, you may find some string like `{ID}`. This is a placeholder to be replaced by the benchmarking tool to differentiate multiple test runs specified in one test specification, as in the above item.

## Stand alone benchmark run
The `harness.py` is the entry point for one benchmark run. It collects the runtime for an entire net and/or individual operator, and saves the data locally or pushes to a remote server. The usage of the script is as follows:

```
usage: harness.py [-h] [--android_dir ANDROID_DIR] [--backend BACKEND]
                  --benchmark_file BENCHMARK_FILE [--devices DEVICES]
                  [--excluded_devices EXCLUDED_DEVICES] --framework {caffe2}
                  --info INFO [--local_reporter LOCAL_REPORTER] --model_cache
                  MODEL_CACHE --platform PLATFORM [--program PROGRAM]
                  [--regressed_types REGRESSED_TYPES]
                  [--remote_reporter REMOTE_REPORTER]
                  [--remote_access_token REMOTE_ACCESS_TOKEN]
                  [--run_type {benchmark,verify,regress}]
                  [--shared_libs SHARED_LIBS] --specifications_dir
                  SPECIFICATIONS_DIR [--timeout TIMEOUT]

Perform one benchmark run

optional arguments:
  -h, --help            show this help message and exit
  --android_dir ANDROID_DIR
                        The directory in the android device all files are
                        pushed to.
  --backend BACKEND     Specify the backend the test runs on.
  --benchmark_file BENCHMARK_FILE
                        Specify the json file for the benchmark or a number of
                        benchmarks
  --devices DEVICES     Specify the devices to run the benchmark, in a comma
                        separated list. The value is the device or device_hash
                        field of the meta info.
  --excluded_devices EXCLUDED_DEVICES
                        Specify the devices that skip the benchmark, in a
                        comma separated list. The value is the device or
                        device_hash field of the meta info.
  --framework {caffe2}  Specify the framework to benchmark on.
  --info INFO           The json serialized options describing the control and
                        treatment.
  --local_reporter LOCAL_REPORTER
                        Save the result to a directory specified by this
                        argument.
  --model_cache MODEL_CACHE
                        The local directory containing the cached models. It
                        should not be part of a git directory.
  --platform PLATFORM   Specify the platform to benchmark on. Use this flag if
                        the framework needs special compilation scripts. The
                        scripts are called build.sh saved in
                        specifications/frameworks/<framework>/<platform>
                        directory
  --program PROGRAM     The program to run on the platform.
  --regressed_types REGRESSED_TYPES
                        A json string that encodes the types of the regressed
                        tests.
  --remote_reporter REMOTE_REPORTER
                        Save the result to a remote server. The style is
                        <domain_name>/<endpoint>|<category>
  --remote_access_token REMOTE_ACCESS_TOKEN
                        The access token to access the remote server
  --run_type {benchmark,verify,regress}
                        The type of the current run. The allowed values are:
                        benchmark, the normal benchmark run. verify, the
                        benchmark is re-run to confirm a suspicious
                        regression. regress, the regression is confirmed.
  --shared_libs SHARED_LIBS
                        Pass the shared libs that the framework depends on, in
                        a comma separated list.
  --specifications_dir SPECIFICATIONS_DIR
                        Required. The root directory that all specifications
                        resides. Usually it is the specifications directory.
  --timeout TIMEOUT     Specify a timeout running the test on the platforms.
                        The timeout value needs to be large enough so that the
                        low end devices can safely finish the execution in
                        normal conditions. Note, in A/B testing mode, the test
                        runs twice.
```

## Continuous benchmark run
The `git_driver.py` is the entry point to run the benchmark continuously. It repeatedly pulls the framework from github, builds the framework, and launches the `harness.py` with the built benchmarking binaries

The accepted arguments are as follows:

```
usage: git_driver.py [-h] --exec_dir EXEC_DIR --framework {caffe2}
                     [--git_base_commit GIT_BASE_COMMIT]
                     [--git_branch GIT_BRANCH] [--git_commit GIT_COMMIT]
                     [--git_commit_file GIT_COMMIT_FILE] --git_dir GIT_DIR
                     [--git_repository GIT_REPOSITORY] [--interval INTERVAL]
                     --platform PLATFORM [--regression] [--same_host]
                     --specifications_dir SPECIFICATIONS_DIR
                     [--status_file STATUS_FILE]

Perform one benchmark run

optional arguments:
  -h, --help            show this help message and exit
  --exec_dir EXEC_DIR   The executable is saved in the specified directory. If
                        an executable is found for a commit, no re-compilation
                        is performed. Instead, the previous compiled
                        executable is reused.
  --framework {caffe2}  Specify the framework to benchmark on.
  --git_base_commit GIT_BASE_COMMIT
                        In A/B testing, this is the control commit that is
                        used to compare against. If not specified, the default
                        is the first commit in the week in UTC timezone. Even
                        if specified, the control is the later of the
                        specified commit and the commit at the start of the
                        week.
  --git_branch GIT_BRANCH
                        The remote git repository branch. Defaults to master
  --git_commit GIT_COMMIT
                        The git commit this benchmark runs on. It can be a
                        branch. Defaults to master. If it is a commit hash,
                        and program runs on continuous mode, it is the
                        starting commit hash the regression runs on. The
                        regression runs on all commits starting from the
                        specified commit.
  --git_commit_file GIT_COMMIT_FILE
                        The file saves the last commit hash that the
                        regression has finished. If this argument is specified
                        and is valid, the --git_commit has no use.
  --git_dir GIT_DIR     Required. The base git directory for Caffe2.
  --git_repository GIT_REPOSITORY
                        The remote git repository. Defaults to origin
  --interval INTERVAL   The minimum time interval in seconds between two
                        benchmark runs.
  --platform PLATFORM   Specify the platform to benchmark on. Use this flag if
                        the framework needs special compilation scripts. The
                        scripts are called build.sh saved in
                        specifications/frameworks/<framework>/<platform>
                        directory
  --regression          Indicate whether this run detects regression.
  --same_host           Specify whether the build and benchmark run are on the
                        same host. If so, the build cannot be done in parallel
                        with the benchmark run.
  --specifications_dir SPECIFICATIONS_DIR
                        Required. The root directory that all specifications
                        resides. Usually it is the specifications directory.
  --status_file STATUS_FILE
                        A file to inform the driver stops running when the
                        content of the file is 0.
```

The `git_driver.py` can also take the arguments that are recognized by `harness.py`. It just passes those arguments over.
