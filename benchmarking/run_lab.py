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
import datetime
from io import StringIO
import json
import logging
import multiprocessing
import os
import shutil
import stat
import sys
import tempfile
import threading
import time

from bridge.file_storages import UploadDownloadFiles
from bridge.db import DBDriver
from download_benchmarks.download_benchmarks import DownloadBenchmarks
from get_connected_devices import GetConnectedDevices
from harness import BenchmarkDriver
from platforms.android.adb import ADB
from reboot_device import reboot as reboot_device
from utils.check_argparse import claimer_id_type
from utils.custom_logger import getLogger, setLoggerLevel
from utils.utilities import getFilename


parser = argparse.ArgumentParser(description="Run the benchmark remotely")

parser.add_argument("--android_dir", default="/data/local/tmp/",
    help="The directory in the android device all files are pushed to.")
parser.add_argument("--app_id",
    help="The app id you use to upload/download your file for everstore "
    "and access the job queue")
parser.add_argument("--claimer_id", required=True, type=claimer_id_type,
    help="A unique claimer id to represent itself. Must talk to Caffe2 team "
    "to set it up.")
parser.add_argument("--cooldown", default=0, type=float,
    help="Specify the time interval between two test runs.")
parser.add_argument("-d", "--devices",
    help="Specify the devices to run the benchmark, in a comma separated "
    "list. The value is the device or device_hash field of the meta info.")
parser.add_argument("--job_queue",
    default="aibench_interactive",
    help="Specify the db job queue that the benchmark is sent to")
parser.add_argument("--logger_level", default="info",
    choices=["info", "warning", "error"],
    help="Specify the logger level")
parser.add_argument("--model_cache", required=True,
    help="The local directory containing the cached models. It should not "
    "be part of a git directory.")
parser.add_argument("--monsoon_map",
    help="Map the phone hash to the monsoon serial number.")
parser.add_argument("-p", "--platform", required=True,
    help="Specify the platform to benchmark on. Use this flag if the framework"
    " needs special compilation scripts. The scripts are called build.sh "
    "saved in specifications/frameworks/<framework>/<platform> directory")
parser.add_argument("--platform_sig",
    help="Specify the platform signature")
parser.add_argument("--reboot", action="store_true",
    help="Tries to reboot the devices before launching benchmarks for one "
    "commit.")
parser.add_argument("--remote_reporter", required=True,
    help="Save the result to a remote server. "
    "The style is <domain_name>/<endpoint>|<category>")
parser.add_argument("--simple_local_reporter", action="store_true",
    help="Save the result to a tmp directory.")
parser.add_argument("--remote_access_token", default="",
    help="The access token to access the remote server")
parser.add_argument("--root_model_dir",
    help="The root model directory if the meta data of the model uses "
    "relative directory, i.e. the location field starts with //")
parser.add_argument("--shared_libs",
    help="Pass the shared libs that the framework depends on, "
    "in a comma separated list.")
parser.add_argument("--status_file",
    help="A file to inform the driver stops running when the content of the file is 0.")
parser.add_argument("--test", action="store_true",
    help="Indicate whether this is a test run. Test runs use a different database.")
parser.add_argument("--timeout", default=300, type=float,
    help="Specify a timeout running the test on the platforms. "
    "The timeout value needs to be large enough so that the low end devices "
    "can safely finish the execution in normal conditions. Note, in A/B "
    "testing mode, the test runs twice. ")
parser.add_argument("--token",
    help="The token you use to upload/download your file for everstore "
    "and access the job queue")
parser.add_argument("--hash_platform_mapping",
    default=None,
    help="Specify the devices hash platform mapping json file.")
parser.add_argument("--file_storage",
    help="The storage engine for uploading and downloading files")
parser.add_argument("--benchmark_db_entry",
    help="The entry point of server's database")
parser.add_argument("--server_addr",
    help="The lab's server address")
parser.add_argument("--benchmark_db",
    help="The database that will store benchmark infos")
parser.add_argument("--benchmark_table",
    help="The table that will store benchmark infos")

REBOOT_INTERVAL = datetime.timedelta(hours=8)
LOCK = threading.RLock()
LOG_LIMIT = 16 * (10**6)


def stopRun(args):
    if args.status_file and os.path.isfile(args.status_file):
        with open(args.status_file, "r") as file:
            content = file.read().strip()
            if content == "0":
                return True
    return False


def getDevicesString(devices):
    device_list = [d["kind"] + "|"
        + d["hash"] + "|"
        + ("1" if d["available"]
             else "0" if d["live"] else "2")
        for d in devices]
    devices_str = ",".join(device_list)
    return devices_str


class runAsync(object):
    def __init__(self, args, devices, db, job, tempdir):
        self.args = args
        self.devices = devices
        self.db = db
        self.job = job
        self.tempdir = tempdir

    def __call__(self, raw_args):
        return self.run(raw_args)

    def run(self, raw_args):
        log_capture_string = StringIO()
        ch = logging.StreamHandler(log_capture_string)
        ch.setLevel(logging.DEBUG)
        getLogger().addHandler(ch)

        try:
            app = BenchmarkDriver(raw_args=raw_args)
            status = app.run()
        except Exception:
            msg = " ".join(raw_args)
            getLogger().error(msg)

        output = log_capture_string.getvalue()
        log_capture_string.close()
        getLogger().handlers.pop()
        getLogger().debug("RunBenchmark")

        return {"status": status, "output": output}

    def callback(self, result_dict):
        with LOCK:
            device = self._updateDevices(result_dict)
            self._submitDone(device)
            self._removeBenchmarkFiles()
            self._coolDown(device)
        time.sleep(1)

    def error_callback(self, *args):
        msg = " ".join(args)
        getLogger().error(msg)

    def _coolDown(self, device):
        force_reboot = self.job["status"] != "DONE"
        t = CoolDownDevice(device, self.args, self.db, force_reboot)
        t.start()

    def _updateDevices(self, result_dict):
        status = result_dict["status"]
        output = result_dict["output"]

        if status == 0:
            self.job["status"] = "DONE"
        elif status == 1:
            self.job["status"] = "USER_ERROR"
        else:
            self.job["status"] = "FAILED"
        if not output:
            getLogger().error("Error, output are None")
        else:
            outputs = output.split("\n")
            for o in outputs:
                getLogger().info(o)
            if sys.getsizeof(output) > LOG_LIMIT:
                getLogger().error("Error, output are too large")
                output = output[-LOG_LIMIT:]
            self.job["log"] = output

        device = self.devices[self.job["device"]][self.job["hash"]]
        device["output_dir"] = self.tempdir
        device["done_time"] = time.ctime()

        return device

    def _submitDone(self, device):
        data = self._collectBenchmarkData(device["output_dir"])
        log = self._collectLogData(self.job)
        self.db.doneBenchmarks(str(self.job["id"]),
                                self.job["status"],
                                data,
                                log)

    def _removeBenchmarkFiles(self):
        benchmark_file = self.job["benchmarks"]["benchmark"]["content"]
        models_location = self.job["models_location"]
        programs_location = self.job["programs_location"]
        os.remove(benchmark_file)
        for model_location in models_location:
            shutil.rmtree(os.path.dirname(model_location))
        for program_location in programs_location:
            shutil.rmtree(os.path.dirname(program_location))

    def _collectBenchmarkData(self, output_dir):
        data = {}
        dirs = self._listdirs(output_dir)
        for d in dirs:
            f = output_dir + "/" + d + "/data.txt"
            if not os.path.isfile(f):
                getLogger().error("The output {} doesn't exist".format(f))
                continue
            with open(f, "r") as file:
                content = json.load(file)
                # special case for power metrics
                if "power_data" in content:
                    content["power_data"] = \
                        self._handlePowerData(content["power_data"])
                data[d] = content
        return json.dumps(data)

    def _listdirs(self, path):
        return [x for x in os.listdir(path) if os.path.isdir(path + "/" + x)]

    def _handlePowerData(self, filename):
        if not os.path.isfile(filename):
            getLogger().error("Power data file "
                "{} doesn't exist".format(filename))
            return
        app = UploadDownloadFiles(self.args)
        file_link = app.upload(file=filename, permanent=False)
        # remove the temporary file
        os.remove(filename)
        return file_link

    def _collectLogData(self, job):
        return job["log"]


class CoolDownDevice(threading.Thread):
    def __init__(self, device, args, db, force_reboot):
        threading.Thread.__init__(self)
        self.device = device
        self.args = args
        self.db = db
        self.force_reboot = force_reboot

    def run(self):
        reboot = self.args.reboot and \
            (self.force_reboot
            or self.device["reboot_time"] + REBOOT_INTERVAL
            < datetime.datetime.now())
        assert self.device["available"] is False, \
            "The device to cool down should not be available"
        success = True
        if reboot:
            raw_args = []
            raw_args.extend(["--platform", self.args.platform])
            raw_args.extend(["--device", self.device["hash"]])
            raw_args.extend(["--android_dir", self.args.android_dir])
            reboot_device(raw_args=raw_args)
            time.sleep(120)
            self.device["reboot_time"] = datetime.datetime.now()
        if self.args.reboot:
            # for ios/android
            time.sleep(180)
        else:
            time.sleep(20)
        with LOCK:
            getLogger().debug("CoolDownDevice lock acquired")
            if success:
                self.device["available"] = True
            else:
                self.device["live"] = False
            device_str = getDevicesString([self.device])
            self.db.updateDevices(self.args.claimer_id, device_str, False)
        getLogger().debug("CoolDownDevice lock released")
        getLogger().info("Device {}({}) available".format(
            self.device["kind"], self.device["hash"]))


class RunLab(object):
    def __init__(self, raw_args=None):
        self.args, self.unknowns = parser.parse_known_args(raw_args)
        self.benchmark_downloader = DownloadBenchmarks(self.args, getLogger())
        self.adb = ADB(None, self.args.android_dir)
        devices = self._getDevices()
        setLoggerLevel(self.args.logger_level)
        if not self.args.benchmark_db_entry:
            assert self.args.server_addr is not None, \
                "Either server_addr or benchmark_db_entry must be specified"
            while self.args.server_addr[-1] == '/':
                self.args.server_addr = self.args.server_addr[:-1]
            self.args.benchmark_db_entry = self.args.server_addr + "/benchmark/"
        self.db = DBDriver(self.args.benchmark_db,
                           self.args.app_id,
                           self.args.token,
                           self.args.benchmark_table,
                           self.args.job_queue,
                           self.args.test,
                           self.args.benchmark_db_entry)
        self.devices = {}
        for k in devices:
            kind = k["kind"]
            hash = k["hash"]
            entry = {
                "kind": kind,
                "hash": hash,
                "available": True,
                "live": True,
                "start_time": None,
                "done_time": None,
                "output_dir": None,
                "job": None,
                "adb": ADB(hash, self.args.android_dir),
                "reboot_time": datetime.datetime.now() - datetime.timedelta(hours=8)
            }
            if kind not in self.devices:
                self.devices[kind] = {}
            assert hash not in self.devices[kind], \
                "Device {} ({}) is attached twice.".format(kind, hash)
            self.devices[kind][hash] = entry

        dvs = [self.devices[k][h] for k in self.devices for h in self.devices[k]]
        self.db.updateDevices(self.args.claimer_id,
                               getDevicesString(dvs), True)
        if self.args.platform.startswith("host"):
            numProcesses = 2
        else:
            numProcesses = multiprocessing.cpu_count() - 1
        self.pool = multiprocessing.Pool(processes=numProcesses)

    def run(self):
        while(not stopRun(self.args)):
            with LOCK:
                self._runOnce()
            time.sleep(1)
        self.db.updateDevices(self.args.claimer_id, "", True)

    def _runOnce(self):
        jobs = self._claimBenchmarks()
        jobs_queue, remaining_jobs = self._selectBenchmarks(jobs)
        if len(remaining_jobs) != 0:
            self._releaseBenchmarks(remaining_jobs)
        if len(jobs_queue) == 0:
            return
        self._runBenchmarks(jobs_queue)

    def _claimBenchmarks(self):
        claimer_id = self.args.claimer_id
        # get available devices
        devices = ",".join([k for k in self.devices
                            if any(self.devices[k][hash]["available"] is True
                            for hash in self.devices[k])])
        jobs = []
        if len(devices) > 0:
            jobs = self.db.claimBenchmarks(claimer_id, devices)
        return jobs

    def _selectBenchmarks(self, jobs):
        remaining_jobs = []
        jobs_queue = []
        for job in jobs:
            device_kind = job["device"]
            if device_kind not in self.devices:
                getLogger().error("Retrieved job for device "
                                  "{} ".format(device_kind)
                                  + "cannot be run on server "
                                  "{}".format(self.args.claimer_id))
                remaining_jobs.append(job)
            else:
                for hash in self.devices[device_kind]:
                    device = self.devices[device_kind][hash]
                    if device["available"] is True:
                        job["hash"] = hash
                        jobs_queue.append(job)
                        device["available"] = False
                        break
        return jobs_queue, remaining_jobs

    def _releaseBenchmarks(self, remaining_jobs):
        # releasing unmatched jobs
        releasing_ids = ",".join([str(job["id"]) for job in remaining_jobs])
        self.db.releaseBenchmarks(self.args.claimer_id, releasing_ids)

    def _runBenchmarks(self, jobs_queue):
        # run the jobs in job queue
        run_ids = ",".join([str(job["id"]) for job in jobs_queue])
        self.db.runBenchmarks(self.args.claimer_id, run_ids)
        run_devices = [self.devices[job["device"]][job["hash"]]
                       for job in jobs_queue]
        self.db.updateDevices(self.args.claimer_id,
                               getDevicesString(run_devices), False)
        self._downloadFiles(jobs_queue)

        # run the benchmarks
        for job in jobs_queue:
            tempdir = tempfile.mkdtemp()
            raw_args = self._getRawArgs(job, tempdir)
            self.devices[job["device"]][job["hash"]]["start_time"] = time.ctime()
            app = runAsync(self.args, self.devices, self.db, job, tempdir)

            """
            Python's multiprocessing need to pickle things to sling them
            in different processes. However, bounded methods are not pickable,
            so the way it's doing it here doesn't work.
            Thus, I added __call__ method in runAsync class and call the
            class here, since class object is pickable.
            Ref: https://stackoverflow.com/a/6975654
            """
            self.pool.apply_async(app, args=[raw_args],
                callback=app.callback)

    def _saveBenchmarks(self, job):
        # save benchmarks to files
        benchmarks = job["benchmarks"]
        benchmark = benchmarks["benchmark"]
        content = benchmark["content"]
        benchmark_str = json.dumps(content)
        outfd, path = tempfile.mkstemp()
        with os.fdopen(outfd, "w") as f:
            f.write(benchmark_str)
        job["benchmarks"]["benchmark"]["content"] = path
        if content["tests"][0]["metric"] == "generic":
            job["framework"] = "generic"
        elif "model" in content and "framework" in content["model"]:
            job["framework"] = content["model"]["framework"]
        else:
            getLogger().error("Framework is not specified, "
                "use Caffe2 as default")
            job["framework"] = "caffe2"
        return path

    def _downloadBinaries(self, info_dict):
        programs = info_dict["programs"]
        program_locations = []
        for bin_name in programs:
            program_location = programs[bin_name]["location"]
            self.benchmark_downloader.downloadFile(program_location, None)
            if program_location.startswith("//"):
                program_location = self.args.root_model_dir + program_location[1:]
            elif program_location.startswith("http"):
                replace_pattern = {
                    " ": '-',
                    "\\": '-',
                    ":": '/',
                }
                program_location = self.args.root_model_dir + '/' +\
                                   getFilename(program_location,
                                               replace_pattern=replace_pattern)
            elif program_location.startswith("/"):
                program_location = self.args.root_model_dir + program_location
            if self.args.platform.startswith("ios") and \
                    bin_name == "program" and \
                    not program_location.endswith(".ipa"):
                new_location = program_location + ".ipa"
                os.rename(program_location, new_location)
                program_location = new_location
            os.chmod(program_location, stat.S_IXUSR | stat.S_IRUSR | stat.S_IWUSR)
            programs[bin_name]["location"] = program_location
            program_locations.append(program_location)
        return program_locations

    def _downloadFiles(self, jobs_queue):
        for job in jobs_queue:
            job["models_location"] = []
            # download the models
            path = self._saveBenchmarks(job)
            location = self.benchmark_downloader.run(path)
            job["models_location"].extend(location)
            # download the programs
            if "info" not in job["benchmarks"]:
                continue
            try:
                if "treatment" not in job["benchmarks"]["info"]:
                    getLogger().error("Field treatment "
                        "must exist in job[\"benchmarks\"]")
                elif "programs" not in job["benchmarks"]["info"]["treatment"]:
                    getLogger().error("Field \"program\" must exist in "
                        "job[\"benchmarks\"][\"info\"][\"treatment\"]")
                else:
                    treatment_info = job["benchmarks"]["info"]["treatment"]
                    treatment_locations = self._downloadBinaries(treatment_info)
                    job["programs_location"] = treatment_locations

                if "control" in job["benchmarks"]["info"]:
                    if "programs" not in job["benchmarks"]["info"]["control"]:
                        getLogger().error("Field \"program\" must exist in "
                            "job[\"benchmarks\"][\"info\"][\"control\"]")
                    else:
                        control_info = job["benchmarks"]["info"]["control"]
                        control_locations = self._downloadBinaries(control_info)
                        job["programs_location"].append(control_locations)

            except Exception:
                getLogger().error("Unknown exception {}".format(sys.exc_info()[0]))
                getLogger().error("File download failure")

    def _getDevices(self):
        raw_args = []
        raw_args.extend(["--platform", self.args.platform])
        if self.args.platform_sig:
            raw_args.append("--platform_sig")
            raw_args.append(self.args.platform_sig)
        if self.args.devices:
            raw_args.append("--devices")
            raw_args.append(self.args.devices)
        if self.args.hash_platform_mapping:
            # if the user provides filename, we will load it.
            raw_args.append("--hash_platform_mapping")
            raw_args.append(self.args.hash_platform_mapping)
        app = GetConnectedDevices(raw_args=raw_args)
        devices_json = app.run()
        assert devices_json, "Devices cannot be empty"
        devices = json.loads(devices_json.strip())
        return devices

    def _getRawArgs(self, job, tempdir):
        if "info" in job["benchmarks"]:
            info = job["benchmarks"]["info"]
        elif "program" in job["benchmarks"]:
            # TODO: remove after all clients are updated
            info = {
                "treatment": {
                    "commit": "interactive",
                    "commit_time": 0,
                    "program": job["benchmarks"]["program"],
                }
            }
        # pass the device hash as well as type
        device = {
            "kind": job["device"],
            "hash": job["hash"]
        }
        device_str = json.dumps(device)
        raw_args = []
        raw_args.extend([
            "--benchmark_file", job["benchmarks"]["benchmark"]["content"],
            "--cooldown", str(self.args.cooldown),
            "--device", device_str,
            "--framework", job["framework"],
            "--info", json.dumps(info),
            "--model_cache", self.args.model_cache,
            "--platform", self.args.platform,
            "--remote_access_token", self.args.remote_access_token,
            "--root_model_dir", self.args.root_model_dir,
            "--user_identifier", str(job["identifier"]),
        ])
        if job["framework"] != "generic":
            raw_args.extend(["--remote_reporter", self.args.remote_reporter])
        if self.args.shared_libs:
            raw_args.extend(["--shared_libs", "'" + self.args.shared_libs + "'"])
        if self.args.timeout:
            raw_args.extend(["--timeout", str(self.args.timeout)])
        if self.args.platform_sig:
            raw_args.append("--platform_sig")
            raw_args.append(self.args.platform_sig)
        if self.args.monsoon_map:
            raw_args.extend(["--monsoon_map", str(self.args.monsoon_map)])
        if self.args.hash_platform_mapping:
            # if the user provides filename, we will load it.
            raw_args.append("--hash_platform_mapping")
            raw_args.append(self.args.hash_platform_mapping)
        if self.args.simple_local_reporter:
            raw_args.append("--simple_local_reporter")
            raw_args.append(tempdir)

        return raw_args


if __name__ == "__main__":
    raw_args = None
    app = RunLab(raw_args=raw_args)
    app.run()
