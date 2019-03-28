#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
from getpass import getuser
import json
import os
from random import randint
import re
import shutil
import tempfile
import threading
import subprocess

from bridge.db import DBDriver
from remote.devices import Devices
from remote.file_handler import FileHandler
from remote.screen_reporter import ScreenReporter
from remote.print_result_url import PrintResultURL
from utils.build_program import buildProgramPlatform
from utils.custom_logger import getLogger, setLoggerLevel
from utils.utilities import getBenchmarks, getMeta, parse_kwarg

parser = argparse.ArgumentParser(description="Run the benchmark remotely")
parser.add_argument("--async_submit", action="store_true",
    help="Return once the job has been submitted to db. No need to wait till "
    "finish so that you can submit mutiple jobs in async way.")
parser.add_argument("--app_id",
    help="The app id you use to upload/download your file for everstore "
    "and access the job queue")
parser.add_argument("-b", "--benchmark_file",
    help="Specify the json file for the benchmark or a number of benchmarks")
parser.add_argument("--cache_config", required=True,
    help="The config file to specify the cached uploaded files. If the files "
    "are already uploaded in the recent past, do not upload again.")
parser.add_argument("-c", "--custom_binary",
    help="Specify the custom binary that you want to run.")
parser.add_argument("--pre_built_binary",
    help="Specify the pre_built_binary to bypass the building process.")
parser.add_argument("--debug", action="store_true",
            help="Debug mode to retain all the running binaries and models.")
parser.add_argument("--devices",
    help="Specify the devices to benchmark on, in comma separated list.")
parser.add_argument("--devices_config", default=None,
    help="The config file in absolute path to map abbreviations to full names")
parser.add_argument("--env", help="environment variables passed to runtime binary")
parser.add_argument("--fetch_status", action="store_true",
    help="Fetch the status of already submitted jobs, use together with "
    "--user_identifier")
parser.add_argument("--fetch_result", action="store_true",
    help="Fetch the result of already submitted jobs, use together with "
    "--user_identifier")
parser.add_argument("--framework",
    choices=["caffe2", "generic", "oculus", "tflite"],
    help="Specify the framework to benchmark on.")
parser.add_argument("--frameworks_dir", default=None,
    help="The root directory that all frameworks resides. "
    "Usually it is the specifications/frameworks directory. "
    "If not provide, we will try to find it from the binary.")
parser.add_argument("--info",
    help="The json serialized options describing the control and treatment.")
parser.add_argument("--job_queue",
    default="aibench_interactive",
    help="Specify the db job queue that the benchmark is sent to")
parser.add_argument("--list_devices", action="store_true",
    help="List the devices associated to the job queue")
parser.add_argument("--list_job_queues", action="store_true",
    help="List the job queues that have available devices")
parser.add_argument("--logger_level", default="warning",
    choices=["info", "warning", "error"],
    help="Specify the logger level")
parser.add_argument("--string_map",
    help="The json serialized arguments passed into treatment for remote run.")
parser.add_argument("--platform",
    help="Specify the platform to benchmark on."
    "Use this flag if the framework"
    " needs special compilation scripts. The scripts are called build.sh "
    "saved in specifications/frameworks/<framework>/<platforms> directory")
parser.add_argument("--force_submit", action="store_true",
    help="Force to submit the run.")
parser.add_argument("--repo_dir",
    help="Required. The base framework repo directory used for benchmark.")
parser.add_argument("--root_model_dir",
    help="The root model directory if the meta data of the model uses "
    "relative directory, i.e. the location field starts with //")
parser.add_argument("--screen_reporter", action="store_true",
    help="Display the summary of the benchmark result on screen.")
parser.add_argument("--test", action="store_true",
    help="Indicate whether this is a test run. Test runs use a different database.")
parser.add_argument("--token",
    help="The token you use to upload/download your file for everstore "
    "and access the job queue")
parser.add_argument("--user_identifier",
    help="The identifier user pass in to differentiate different benchmark runs.")
parser.add_argument("--user_string",
    help="The user_string pass in to differentiate different regression benchmark runs.")
parser.add_argument("--file_storage",
    help="The storage engine for uploading and downloading files")
parser.add_argument("--benchmark_db_entry",
    help="The entry point of server's database")
parser.add_argument("--server_addr",
    help="The lab's server address")
parser.add_argument("--result_db",
    help="The database that will store benchmark results")
parser.add_argument("--benchmark_db",
    help="The database that will store benchmark infos")
parser.add_argument("--benchmark_table",
    help="The table that will store benchmark infos")


class BuildProgram(threading.Thread):
    def __init__(self, args, file_handler, tempdir, filenames, prebuilt_binary=None):
        threading.Thread.__init__(self)
        self.tempdir = tempdir
        self.args = args
        self.file_handler = file_handler
        self.filenames = filenames
        self.prebuilt_binary = prebuilt_binary

    def run(self):
        self._buildProgram(self.tempdir)

    def _buildProgram(self, tempdir):
        # build binary
        platform = self.args.platform
        program = tempdir + "/program"
        if os.name == "nt":
            program = program + ".exe"
        elif platform.startswith("ios"):
            program = program + ".ipa"
        if self.prebuilt_binary:
            program = self.prebuilt_binary
        else:
            print("Building program...")
            success = buildProgramPlatform(program, self.args.repo_dir,
                                           self.args.framework,
                                           self.args.frameworks_dir,
                                           self.args.platform)
            if not success:
                return

        # upload all files under the fname directory
        filedir = os.path.dirname(program)
        allfiles = []
        if os.path.exists(filedir):
            if self.prebuilt_binary:
                allfiles = [program]
            else:
                allfiles = [os.path.join(filedir, f) for f in os.listdir(filedir)]

            for fn in allfiles:
                filename, _ = self.file_handler.uploadFile(fn, None, None, False)
                getLogger().info("program: {}".format(filename))
                self.filenames[os.path.basename(fn)] = filename
            # main program needs to be in
            self.filenames["program"] = self.filenames[os.path.basename(program)]
        else:
            self.filenames["program"] = program


class RunRemote(object):
    def __init__(self, raw_args=None):
        self.args, self.unknowns = parser.parse_known_args(raw_args)
        setLoggerLevel(self.args.logger_level)
        if not self.args.benchmark_db_entry:
            self.args.benchmark_db_entry = self.args.server_addr + "benchmark/"
        self.db = DBDriver(self.args.benchmark_db,
                           self.args.app_id,
                           self.args.token,
                           self.args.benchmark_table,
                           self.args.job_queue,
                           self.args.test,
                           self.args.benchmark_db_entry)
        self.url_printer = PrintResultURL(self.args)
        self.file_handler = FileHandler(self.args)
        self.devices = Devices(self.args.devices_config)
        # Hard code scuba table
        self.scuba_dataset = "caffe2_benchmarking"
        self.info = None
        self.temprdir = ''

    def run(self):
        if self.args.list_devices:
            self._listDevices()
            return
        if self.args.list_job_queues:
            self._printJobQueues()
            return
        if self.args.fetch_status or self.args.fetch_result:
            result = self._fetchResult()
            return result

        assert self.args.benchmark_file, \
            "--benchmark_file (-b) must be specified"
        assert self.args.devices, "--devices must be specified"
        assert self.args.framework, "--framework must be specified"
        assert self.args.platform, "--platform must be specified"
        assert self.args.repo_dir, "--repo_dir must be specified"
        assert ((self.args.info is not None) and
            (self.args.custom_binary is None) and
            (self.args.pre_built_binary is None)) or (self.args.info is None), \
            "--info cannot co-exist with --custom_binary and --pre_built_binary"

        list_job_queues = self._listJobQueues()
        if not self.args.force_submit:
            self._checkDevices(self.args.devices)
            assert self.args.job_queue != "*" and \
                self.args.job_queue in list_job_queues, \
                "--job_queue must be choosen from " + " ".join(list_job_queues)

        self.tempdir = tempfile.mkdtemp()
        program_filenames = {}
        if self.args.info:
            self.info = json.loads(self.args.info)
        else:
            self.info = {"treatment": {"programs": {}}}
            if self.args.string_map:
                self.info["treatment"]["string_map"] = str(self.args.string_map)

        assert (("treatment" in self.info) and
                ("programs" in self.info["treatment"])), \
            'In --info, field treatment must exist. In info["treatment"] ' \
            "program field must exist (may be None)"

        binary = self.info["treatment"]["programs"]["program"]["location"] \
            if ("programs" in self.info["treatment"] and
                "program" in self.info["treatment"]["programs"]) \
            else self.args.custom_binary if self.args.custom_binary \
            else self.args.pre_built_binary
        t = BuildProgram(self.args, self.file_handler,
                         self.tempdir, program_filenames,
                         binary)
        t.start()

        benchmarks = getBenchmarks(self.args.benchmark_file,
                                   self.args.framework)
        for benchmark in benchmarks:
            self._uploadOneBenchmark(benchmark)
            if self.args.debug:
                for test in benchmark["content"]["tests"]:
                    test["log_output"] = True
            if self.args.env:
                env = {}
                env_vars = self.args.env.split()
                for env_var in env_vars:
                    k, v = parse_kwarg(env_var)
                    env[k] = v
                for test in benchmark["content"]["tests"]:
                    cmd_env = {}
                    cmd_env.update(env)
                    if "env" in test:
                        cmd_env.update(test["env"])
                    test["env"] = cmd_env
        t.join()

        assert "program" in program_filenames, \
            "program does not exist. Build may be failed."

        for fn in program_filenames:
            self.info["treatment"]["programs"][fn] = {
                "location": program_filenames[fn]
            }

        # Pass meta file from build to benchmark
        meta = getMeta(self.args, self.args.platform)
        if meta:
            assert "meta" not in self.info, \
                "info field already has a meta field"
            self.info["meta"] = meta

        new_devices = self.devices.getFullNames(self.args.devices)
        user_identifier = int(self.args.user_identifier) \
            if self.args.user_identifier else randint(1, 1000000000000000)
        user = getuser() if not self.args.user_string else self.args.user_string
        for benchmark in benchmarks:
            data = {
                "benchmark": benchmark,
                "info": self.info,
            }
            self.db.submitBenchmarks(data, new_devices, user_identifier, user)
        if self.args.async_submit:
            return
        self.url_printer.printURL(self.scuba_dataset,
                                  user_identifier,
                                  benchmarks)

        if not self.args.debug:
            shutil.rmtree(self.tempdir, True)
        if self.args.screen_reporter:
            self._screenReporter(user_identifier)

    def _uploadOneBenchmark(self, benchmark):
        filename = benchmark["filename"]
        one_benchmark = benchmark["content"]
        # TODO refactor the code to collect all files to upload
        del_paths = []
        if "model" in one_benchmark:
            if "files" in one_benchmark["model"]:
                for field in one_benchmark["model"]["files"]:
                    value = one_benchmark["model"]["files"][field]
                    assert "location" in value, \
                        "location field is missing in benchmark " \
                        "{}".format(filename)
                    ref_path = ["files", field]
                    if self._uploadFile(value, filename, benchmark, ref_path):
                        del_paths.append(ref_path)
            if "libraries" in one_benchmark["model"]:
                for value in one_benchmark["model"]["libraries"]:
                    assert "location" in value, \
                        "location field is missing in benchmark " \
                        "{}".format(filename)
                    self._uploadFile(value, filename, benchmark)

        for del_path in del_paths:
            self._del_from_benchmark(benchmark["content"]["model"], del_path)

        # upload test file
        assert "tests" in one_benchmark, \
            "tests field is missing in benchmark {}".format(filename)
        tests = one_benchmark["tests"]
        for test in tests:
            if "input_files" in test:
                self._uploadTestFiles(test["input_files"], filename)
            # ignore the outputs for non accuracy metrics
            if "output_files" in test and test["metric"] == "error":
                self._uploadTestFiles(test["output_files"], filename)

    def _uploadTestFiles(self, files, basefilename):
        if isinstance(files, list):
            for i in range(len(files)):
                f = files[i]
                self._uploadFile(f, basefilename)
        elif isinstance(files, dict):
            for f in files:
                value = files[f]
                if isinstance(value, list):
                    for i in range(len(value)):
                        v = value[i]
                        self._uploadFile(v, basefilename)
                else:
                    self._uploadFile(value, basefilename)

    def _uploadFile(self, f, basefilename, benchmark=None,
                    ref_path=None, cache_file=True):
        if "location" not in f:
            return
        location = f["location"]
        md5 = f["md5"] if "md5" in f else None
        """
        For the file from repo, there is special handling
        we need to fetch both control and treatment
        , and also move the file from benchmark to info
        Note: Support the file in model first
        """
        if location.startswith("//repo"):
            assert ref_path is not None, "repo is not yet \
                supported for {}".format(location)
            for side in self.info:
                value = self.info[side]
                commit_hash = value["commit"] or "master"
                tgt_file = self._downloadRepoFile(location, self.tempdir, commit_hash)
                f["location"], f["md5"] = self.file_handler.uploadFile(tgt_file, md5,
                                                                        basefilename,
                                                                        cache_file)
                # add to info
                assert len(ref_path), "ref_path must be a path to target file"
                value["programs"][".".join(ref_path)] = {"location": f["location"]}
                # remove from benchmark
                assert benchmark is not None, \
                    "benchmark must be passed into _uploadFile"
            return True
        else:
            f["location"], f["md5"] = self.file_handler.uploadFile(location, md5,
                                                                    basefilename,
                                                                    cache_file)
            return False

    def _downloadRepoFile(self, location, tgt_dir, commit_hash):
        """
        location: //repo/fbsource/fbcode/aibench/...../a.py
        """
        dirs = location[2:].split("/")
        BENCHMARK_DIR = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

        query_exe = os.path.join(BENCHMARK_DIR, "bin/scm_query.par")
        tgt_file = os.path.join(tgt_dir, dirs[-1])
        cmd = [
            query_exe, '--repo', dirs[1],
            '--file_path', '/'.join(dirs[2:]),
            '--target_file', tgt_file,
            '--commit_hash', commit_hash
        ]
        getLogger().info("Downloading {}".format(location))
        subprocess.check_output(cmd)
        return tgt_file

    def _del_from_benchmark(self, benchmark, ref_path):
        tgt = benchmark
        for item in ref_path[:-1]:
            tgt = tgt[item]
        tgt.pop(ref_path[-1])

    def _listDevices(self):
        devices = self.db.listDevices(self.args.job_queue)
        for device in devices:
            abbrs = self.devices.getAbbrs(device["device"])
            print(device["status"] + "\t" +
                  device["device"] +
                  (" (" + ",".join(abbrs) + ")" if abbrs else ""))

    def _checkDevices(self, specified_devices):
        devices = set()
        for device in self.db.listDevices(self.args.job_queue):
            abbrs = self.devices.getAbbrs(device["device"])
            devices.add(device["device"])
            devices.update(set(abbrs if abbrs else ""))
        specifiedDevices = set(specified_devices.split(","))
        deivesNotIn = specifiedDevices.difference(devices)
        if deivesNotIn:
            raise Exception("Devices {}".format(deivesNotIn) +
                " is not available in the job_queue {}".format(self.args.job_queue))

    def _listJobQueues(self):
        devices = self.db.listDevices(job_queue="*")
        list_job_queues = sorted({device['job_queue'] for device in devices})
        return list_job_queues

    def _printJobQueues(self):
        list_job_queues = self._listJobQueues()
        for jobQueue in list_job_queues:
            print(jobQueue)

    def _screenReporter(self, user_identifier):
        reporter = ScreenReporter(self.db, self.devices, self.args.debug)
        reporter.run(user_identifier)

    def _fetchResult(self):
        user_identifier = self.args.user_identifier
        assert user_identifier, "User identifier must be specified for " \
            "fetching the status and/or result of the previously run benchmarks"
        statuses = self.db.statusBenchmarks(user_identifier)
        result = None
        if self.args.fetch_status:
            result = json.dumps(statuses)
        elif self.args.fetch_result:
            ids = ",".join([str(status["id"]) for status in statuses])
            output = self.db.getBenchmarks(ids)
            self._mobilelabResult(output)
            result = json.dumps(output)
        print(result)
        return result

    def _mobilelabResult(self, output):
        # always get the last result
        for item in output:
            raw_result = item["result"]
            if raw_result is None:
                continue
            result = json.loads(raw_result)
            mobilelab_result = {
                "treatment": {},
                "control": {}
            }
            for k in result:
                # k is identifier
                v = result[k]
                for kk in v:
                    vv = v[kk]
                    # update values if only summary exists
                    if "values" not in vv or len(vv["values"]) == 0:
                        if "summary" in vv:
                            if "mean" in vv["summary"]:
                                vv["values"] = [vv["summary"]["mean"]]
                            elif "p50" in vv["summary"]:
                                vv["values"] = [vv["summary"]["p50"]]
                        if "control_summary" in vv:
                            if "mean" in vv["control_summary"]:
                                vv["control_values"] = \
                                    [vv["control_summary"]["mean"]]
                            elif "p50" in vv["control_summary"]:
                                vv["control_values"] = \
                                    [vv["control_summary"]["p50"]]
                    # check values again
                    if "values" not in vv or len(vv["values"]) == 0:
                        continue
                    assert vv["type"], "type is missing in {}".format(kk)
                    assert vv["metric"], "metric is missing in {}".format(kk)
                    if vv["metric"] == "flops":
                        continue
                    unit = vv["unit"] if "unit" in vv else "null"
                    self._mobilelabAddField(mobilelab_result["treatment"],
                                            k, vv["type"], vv["metric"],
                                            vv["values"], unit)
                    if "control_values" in vv:
                        self._mobilelabAddField(mobilelab_result["control"], k,
                                                vv["type"], vv["metric"],
                                                vv["control_values"], unit)

            item["mobilelab_result"] = mobilelab_result

    def _mobilelabAddField(self, output, identifier,
                           type, metric, values, unit):
        key = "{}__{}__{}".format(identifier, type, metric)
        key = re.sub('\W+', '_', key)
        assert key not in output, \
           "duplicate key {}".format(key)
        output[key] = {
            "values": values,
            "metric": metric,
            "type": type,
            "unit": unit,
        }


if __name__ == "__main__":
    raw_args = None
    app = RunRemote(raw_args=raw_args)
    app.run()
