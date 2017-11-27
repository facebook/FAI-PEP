# Caffe2 Benchmark Framework

The Caffe2 benchmark framework is used to provide Caffe2 runtime inferencing information on the host and Android platforms for various models.

It uses an A/B testing methodology that compares the runtime difference between a newer commit (treatment) and an older commit (control). What matters is the relative performance between the commits, as the phone's condition may be different at different times. Running the same tests on two different commit points at the same time removes most of the variations of the phone. This method has shown to improve the precision of detecting performance regressions.

Currently two metrics are collected:

* delay : the delay of running the entire network and/or the delay of running each individual operator.
* error : the error between the values of the outputs running a model and golden outputs.

## Stand alone benchmark run
The `harness.py` is the entry point for one benchmark run. It collects the runtime for an entire net and/or individual operator, and saves the data locally or pushes to a remote server. The usage of the script is as follows:

```
usage: harness.py [-h] [--android_dir ANDROID_DIR] [--android] [--host]
                  [--local_reporter LOCAL_REPORTER]
                  [--remote_reporter REMOTE_REPORTER]
                  [--remote_access_token REMOTE_ACCESS_TOKEN]
                  [--excluded_platforms EXCLUDED_PLATFORMS]
                  [--golden_output_file GOLDEN_OUTPUT_FILE]
                  [--identifier IDENTIFIER] [--info INFO] --init_net INIT_NET
                  [--input INPUT] [--input_dims INPUT_DIMS]
                  [--input_file INPUT_FILE] [--input_type INPUT_TYPE]
                  [--iter ITER] [--metric {delay,error}] --net NET
                  [--output OUTPUT] [--output_folder OUTPUT_FOLDER]
                  [--program PROGRAM]
                  [--regression_direction REGRESSION_DIRECTION]
                  [--run_individual] [--temp_dir TEMP_DIR] [--timeout TIMEOUT]
                  [--warmup WARMUP]

Perform one benchmark run

optional arguments:
  -h, --help            show this help message and exit
  --android_dir ANDROID_DIR
                        The directory in the android device all files are
                        pushed to.
  --android             Run the benchmark on all connected android devices.
  --host                Run the benchmark on the host.
  --local_reporter LOCAL_REPORTER
                        Save the result to a directory specified by this
                        argument.
  --remote_reporter REMOTE_REPORTER
                        Save the result to a remote server. The style is
                        <domain_name>/<endpoint>|<category>
  --remote_access_token REMOTE_ACCESS_TOKEN
                        The access token to access the remote server
  --excluded_platforms EXCLUDED_PLATFORMS
                        Specify the platforms that skip the test, in a comma
                        separated list. For android devices, the specified
                        value is the output of the command: "adb shell getprop
                        ro.product.model". For host, the specified value is
                        The output of python method: "platform.processor()".
  --golden_output_file GOLDEN_OUTPUT_FILE
                        The reference output file that contains the serialized
                        protobuf for the output blobs. If multiple output
                        needed, use comma separated string. Must have the same
                        number of items as output does. The specifying order
                        must be the same.
  --identifier IDENTIFIER
                        A unique identifier to identify this type of run so
                        that it can be filtered out from all other regression
                        runs in the database.
  --info INFO           The json serialized options describing the control and
                        treatment.
  --init_net INIT_NET   The given net to initialize any parameters.
  --input INPUT         Input that is needed for running the network. If
                        multiple input needed, use comma separated string.
  --input_dims INPUT_DIMS
                        Alternate to input_files, if all inputs are simple
                        float TensorCPUs, specify the dimension using comma
                        separated numbers. If multiple input needed, use
                        semicolon to separate the dimension of different
                        tensors.
  --input_file INPUT_FILE
                        Input file that contain the serialized protobuf for
                        the input blobs. If multiple input needed, use comma
                        separated string. Must have the same number of items
                        as input does.
  --input_type INPUT_TYPE
                        Type for the input blob. The supported options
                        are:float, uint8_t. The default is float.
  --iter ITER           The number of iterations to run.
  --metric {delay,error}
                        The metric to collect in this test run. The allowed
                        values are: "delay": the net and operator delay.
                        "error": the error in the output blobs between control
                        and treatment.
  --net NET             The given predict net to benchmark.
  --output OUTPUT       Output that should be dumped after the execution
                        finishes. If multiple outputs are needed, use comma
                        separated string.
  --output_folder OUTPUT_FOLDER
                        The folder that the output should be written to. This
                        folder must already exist in the file system.
  --program PROGRAM     The program to run on the platform.
  --regression_direction REGRESSION_DIRECTION
                        The direction when regression happens. 1 means higher
                        value is regression. -1 means lower value is
                        regression.
  --run_individual      Whether to benchmark individual operators.
  --temp_dir TEMP_DIR   The temporary directory used by the script.
  --timeout TIMEOUT     Specify a timeout running the test on the platforms.
                        The timeout value needs to be large enough so that the
                        low end devices can safely finish the execution in
                        normal conditions. Note, in A/B testing mode, the test
                        runs twice.
  --warmup WARMUP       The number of iterations to warm up.
```

## Continuous benchmark run
The `git_driver.py` is the entry point to run the benchmark continuously. It repeatedly pulls the Caffe2 from github, builds the Caffe2, and launches the `harness.py` for every test specified in the config file. In the config file. An example of config file is as follows:

```
{
  "tests" : [
    {
      "args" : "--identifier \"error-64_3_30_30\" --init_net <models_dir>/squeezenet/squeeze_init_net.pb --net <models_dir>/squeezenet/squeeze_predict_net.pb --metric error --input_dims 64,3,30,30 --input data --input_file <models_dir>/squeezenet/tests/test0/data.txt --warmup 0 --iter 1 --output \"softmaxout\" --golden_output_file <models_dir>/squeezenet/tests/test0/softmaxout.txt",
      "excluded_platforms" : ""
    },
    {
      "args" : "--identifier \"delay-64_3_30_30\" --init_net <models_dir>/squeezenet/squeeze_init_net.pb --net <models_dir>/squeezenet/squeeze_predict_net.pb --metric delay --input_dims 64,3,30,30 --input data --run_individual --warmup 10 --iter 50 ",
      "excluded_platforms" : ""
    }
  ]
}
```

The `<models_dir>` is a placeholder that is replaced by the actual model directory specified in the command line `--models_dir`.

The accepted arguments are as follows:

```
usage: git_driver.py [-h] --config CONFIG [--git_base_commit GIT_BASE_COMMIT]
                     [--git_branch GIT_BRANCH] [--git_commit GIT_COMMIT]
                     [--git_commit_file GIT_COMMIT_FILE] --git_dir GIT_DIR
                     [--git_repository GIT_REPOSITORY] [--interval INTERVAL]
                     --models_dir MODELS_DIR [--status_file STATUS_FILE]
                     [--host | --android]

Perform one benchmark run

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG       Required. The test config file containing all the
                        tests to run
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
  --models_dir MODELS_DIR
                        Required. The root directory that all models resides.
  --status_file STATUS_FILE
                        A file to inform the driver stops running when the
                        content of the file is 0.
  --host                Run the benchmark on the host.
  --android             Run the benchmark on all connected android devices.
```

The `git_driver.py` can also take the arguments that are recognized by `harness.py`. It just passes those arguments over.
