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
import gc
import json
import logging
import multiprocessing
import os
import shutil
import signal
import stat
import tempfile
import threading
import time
from concurrent.futures import ProcessPoolExecutor as Pool
from io import StringIO

from bridge.db import DBDriver
from bridge.file_storages import UploadDownloadFiles
from download_benchmarks.download_benchmarks import DownloadBenchmarks
from harness import BenchmarkDriver
from platforms.android.adb import ADB
from platforms.device_manager import CoolDownDevice, DeviceManager
from platforms.device_manager import DEFAULT_DM_INTERVAL as default_dm_interval
from platforms.device_manager import MINIMUM_DM_INTERVAL as minimum_dm_interval
from platforms.device_manager import getDevicesString
from platforms.device_manager import valid_dm_interval
from utils.check_argparse import claimer_id_type
from utils.custom_logger import getLogger, setLoggerLevel
from utils.log_update_handler import DBLogUpdateHandler
from utils.log_utils import DEFAULT_INTERVAL as default_interval
from utils.log_utils import trimLog, collectLogData, valid_interval
from utils.utilities import DownloadException, BenchmarkArgParseException
from utils.utilities import HARNESS_ERROR_FLAG as HARNESS_ERROR
from utils.utilities import KILLED_FLAG as RUN_KILLED
from utils.utilities import SUCCESS_FLAG as SUCCESS
from utils.utilities import TIMEOUT_FLAG as RUN_TIMEOUT
from utils.utilities import USER_ERROR_FLAG as USER_ERROR
from utils.utilities import getFilename, getMachineId, setRunKilled
from utils.watchdog import WatchDog

parser = argparse.ArgumentParser(description="Run the benchmark remotely")

parser.add_argument(
    "--android_dir",
    default="/data/local/tmp/",
    help="The directory in the android device all files are pushed to.",
)
parser.add_argument(
    "--app_id",
    help="The app id you use to upload/download your file for everstore "
    "and access the job queue",
)
parser.add_argument(
    "--claimer_id",
    default=getMachineId(),
    type=claimer_id_type,
    help="A unique claimer id to represent itself. "
    "Must talk to Caffe2 team to set it up.",
)
parser.add_argument(
    "--cooldown",
    default=0,
    type=float,
    help="Specify the time interval between two test runs.",
)
parser.add_argument(
    "-d",
    "--devices",
    help="Specify the devices to run the benchmark, in a comma separated "
    "list. The value is the device or device_hash field of the meta info.",
)
parser.add_argument(
    "--job_queue",
    default="aibench_interactive",
    help="Specify the db job queue that the benchmark is sent to",
)
parser.add_argument(
    "--logger_level",
    default="info",
    choices=["info", "warning", "error"],
    help="Specify the logger level",
)
parser.add_argument(
    "--model_cache",
    required=True,
    help="The local directory containing the cached models. It should not "
    "be part of a git directory.",
)
parser.add_argument(
    "--monsoon_map", help="Map the phone hash to the monsoon serial number."
)
parser.add_argument(
    "-p",
    "--platform",
    required=True,
    help="Specify the platform to benchmark on. Use this flag if the framework"
    " needs special compilation scripts. The scripts are called build.sh "
    "saved in specifications/frameworks/<framework>/<platform> directory",
)
parser.add_argument("--platform_sig", help="Specify the platform signature")
parser.add_argument(
    "--reboot",
    action="store_true",
    help="Tries to reboot the devices before launching benchmarks for one " "commit.",
)
parser.add_argument(
    "--remote_reporter",
    required=True,
    help="Save the result to a remote server. "
    "The style is <domain_name>/<endpoint>|<category>",
)
parser.add_argument(
    "--remote_access_token",
    default="",
    help="The access token to access the remote server",
)
parser.add_argument(
    "--root_model_dir",
    help="The root model directory if the meta data of the model uses "
    "relative directory, i.e. the location field starts with //",
)
parser.add_argument(
    "--rt_logging", action="store_true", help="Enable realtime logging to database."
)
parser.add_argument(
    "--rt_logging_interval",
    type=valid_interval,
    default=str(default_interval),
    help="Realtime logging Update interval in seconds. Minimum 5 seconds.",
)
parser.add_argument(
    "--device_monitor_interval",
    type=valid_dm_interval,
    default=str(default_dm_interval),
    help="Device monitoring interval in seconds. Minimum {}s, default {}s.".format(
        minimum_dm_interval, default_dm_interval
    ),
)
parser.add_argument(
    "--shared_libs",
    help="Pass the shared libs that the framework depends on, "
    "in a comma separated list.",
)
parser.add_argument(
    "--status_file",
    help="A file to inform the driver stops running when the content of the file is 0.",
)
parser.add_argument(
    "--test",
    action="store_true",
    help="Indicate whether this is a test run. Test runs use a different database.",
)
parser.add_argument(
    "--timeout",
    default=300,
    type=float,
    help="Specify a timeout running the test on the platforms. "
    "The timeout value needs to be large enough so that the low end devices "
    "can safely finish the execution in normal conditions. Note, in A/B "
    "testing mode, the test runs twice. ",
)
parser.add_argument(
    "--token",
    help="The token you use to upload/download your file for everstore "
    "and access the job queue",
)
parser.add_argument(
    "--hash_platform_mapping",
    default=None,
    help="Specify the devices hash platform mapping json file.",
)
parser.add_argument(
    "--device_name_mapping",
    default=None,
    help="Specify device to product name mapping json file.",
)
parser.add_argument(
    "--usb_hub_device_mapping",
    default=None,
    help="Specify the usb hub hash, port mapping to devices",
)
parser.add_argument(
    "--file_storage", help="The storage engine for uploading and downloading files"
)
parser.add_argument("--benchmark_db_entry", help="The entry point of server's database")
parser.add_argument("--server_addr", help="The lab's server address")
parser.add_argument(
    "--benchmark_db", help="The database that will store benchmark infos"
)
parser.add_argument(
    "--benchmark_table", help="The table that will store benchmark infos"
)

LOCK = threading.RLock()

DRAIN = False
RUNNING_JOBS = 0


def drainHandler(signum, frame):
    global DRAIN
    DRAIN = True


def hookSignals():
    signal.signal(signal.SIGUSR1, drainHandler)
    signal.signal(signal.SIGTERM, drainHandler)
    signal.signal(signal.SIGINT, drainHandler)


def stopRun(args):
    global DRAIN
    global RUNNING_JOBS
    if DRAIN and RUNNING_JOBS == 0:
        getLogger().info("Finished draining. Exiting...")
        return True
    if args.status_file and os.path.isfile(args.status_file):
        with open(args.status_file, "r") as file:
            content = file.read().strip()
            if content == "0":
                return True
    return False


class runAsync(object):
    def __init__(self, args, device, db, job, benchmark_downloader, usb_controller):
        self.args = args
        self.device = device
        self.db = db
        self.job = job
        self.tempdir = tempfile.mkdtemp(
            prefix="_".join(["aibench", str(job.get("identifier")), ""])
        )
        self.benchmark_downloader = benchmark_downloader
        self.usb_controller = usb_controller

    def __call__(self):
        return self.run()

    def run(self):
        handlers = []
        log_capture_string = StringIO()
        ch = logging.StreamHandler(log_capture_string)
        ch.setLevel(logging.DEBUG)
        getLogger().addHandler(ch)
        handlers.append(ch)
        # if enabled realtime logger will also update the log entry at regualr intervals.
        if self.args.rt_logging:
            dbh = DBLogUpdateHandler(
                self.db, self.job["id"], self.args.rt_logging_interval
            )
            dbh.setLevel(logging.DEBUG)
            getLogger().addHandler(dbh)
            handlers.append(dbh)
            getLogger().info(
                "Realtime logging enabled with {}s updates.".format(
                    self.args.rt_logging_interval
                )
            )
        try:
            self._setFramework()
            with LOCK:
                self._downloadFiles()
            raw_args = self._getRawArgs()
            app = BenchmarkDriver(raw_args=raw_args, usb_controller=self.usb_controller)
            getLogger().debug(
                f"Running BenchmarkDriver for benchmark {self.job['identifier']} id ({self.job['id']})"
            )
            status = app.run()
        except DownloadException:
            getLogger().exception(
                f"An error occurred while running benchmark {self.job['identifier']} id ({self.job['id']})"
            )
            status = HARNESS_ERROR
        except BenchmarkArgParseException:
            getLogger().exception(
                f"An error occurred while running benchmark {self.job['identifier']} id ({self.job['id']})"
            )
            status = USER_ERROR
        except Exception:
            getLogger().exception(
                f"An error occurred while running benchmark {self.job['identifier']} id ({self.job['id']})"
            )
            status = HARNESS_ERROR
        finally:
            output = log_capture_string.getvalue()
            log_capture_string.close()
            for handler in handlers:
                handler.close()
                getLogger().handlers.remove(handler)
            del handlers
            self._setStatusOutput(status, output)
            self._submitDone()
            self._removeBenchmarkFiles()
            time.sleep(1)

        return {"device": self.device, "job": self.job}

    def _setFramework(self):
        """Set framework of job based on benchmark config.  Default to caffe2"""
        try:
            content = self.job["benchmarks"]["benchmark"]["content"]
            if content["tests"][0]["metric"] == "generic":
                self.job["framework"] = "generic"
            elif "model" in content and "framework" in content["model"]:
                self.job["framework"] = content["model"]["framework"]
            else:
                getLogger().error("Framework is not specified, use Caffe2 as default")
                self.job["framework"] = "caffe2"
        except Exception:
            raise BenchmarkArgParseException("Error parsing raw args from job.")

    def _getRawArgs(self):
        """Create raw args for BenchmarkDriver"""
        try:
            if "info" in self.job["benchmarks"]:
                info = self.job["benchmarks"]["info"]
            # pass the device hash as well as type
            device = {"kind": self.job["device"], "hash": self.job["hash"]}
            device_str = json.dumps(device)
            raw_args = []
            raw_args.extend(
                [
                    "--benchmark_file",
                    self.job["benchmarks"]["benchmark"]["content"],
                    "--cooldown",
                    str(self.args.cooldown),
                    "--device",
                    device_str,
                    "--framework",
                    self.job["framework"],
                    "--info",
                    json.dumps(info),
                    "--model_cache",
                    self.args.model_cache,
                    "--platform",
                    self.args.platform,
                    "--remote_access_token",
                    self.args.remote_access_token,
                    "--root_model_dir",
                    self.args.root_model_dir,
                    "--simple_local_reporter",
                    self.tempdir,
                    "--user_identifier",
                    str(self.job["identifier"]),
                    "--user_string",
                    self.job.get("user"),
                ]
            )
            if self.job["framework"] != "generic":
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
            if self.args.device_name_mapping:
                raw_args.append("--device_name_mapping")
                raw_args.append(self.args.device_name_mapping)
            return raw_args
        except Exception:
            raise BenchmarkArgParseException("Error parsing raw args from job.")

    def _saveBenchmarks(self):
        """Save benchmark config to file"""
        content = self.job["benchmarks"]["benchmark"]["content"]
        benchmark_str = json.dumps(content)
        path = self.tempdir + "benchmark"
        with open(path, "w") as f:
            f.write(benchmark_str)
        self.job["benchmarks"]["benchmark"]["content"] = path
        return path

    def _downloadBinaries(self, info_dict):
        """Download benchmark binaries and return locations."""
        programs = info_dict["programs"]
        program_locations = []
        for bin_name in programs:
            program_location = programs[bin_name]["location"]
            self.benchmark_downloader.downloadFile(program_location, None)
            if program_location.startswith("//"):
                program_location = self.args.root_model_dir + program_location[1:]
            elif program_location.startswith("http"):
                replace_pattern = {
                    " ": "-",
                    "\\": "-",
                    ":": "/",
                }
                program_location = os.path.join(
                    self.args.root_model_dir,
                    getFilename(program_location, replace_pattern=replace_pattern),
                )
            elif program_location.startswith("/"):
                program_location = self.args.root_model_dir + program_location
            if (
                self.args.platform.startswith("ios")
                and bin_name == "program"
                and not program_location.endswith(".ipa")
            ):
                new_location = program_location + ".ipa"
                os.rename(program_location, new_location)
                program_location = new_location
            os.chmod(program_location, stat.S_IXUSR | stat.S_IRUSR | stat.S_IWUSR)
            programs[bin_name]["location"] = program_location
            program_locations.append(program_location)
        return program_locations

    def _downloadFiles(self):
        """Download benchmark files."""
        try:
            # Download models
            self.job["models_location"] = []
            getLogger().info(
                f"Downloading models for benchmark {self.job['identifier']} id {self.job['id']}"
            )
            path = self._saveBenchmarks()
            location = self.benchmark_downloader.run(path)
            self.job["models_location"].extend(location)
            # Download programs
            if "info" in self.job["benchmarks"]:
                getLogger().info(
                    f"Downloading programs for benchmark {self.job['identifier']} id {self.job['id']}"
                )
                if "treatment" not in self.job["benchmarks"]["info"]:
                    getLogger().error(
                        "Field treatment " 'must exist in job["benchmarks"]'
                    )
                elif "programs" not in self.job["benchmarks"]["info"]["treatment"]:
                    getLogger().error(
                        'Field "program" must exist in '
                        'job["benchmarks"]["info"]["treatment"]'
                    )
                else:
                    treatment_info = self.job["benchmarks"]["info"]["treatment"]
                    getLogger().info("Downloading treatment binary")
                    treatment_locations = self._downloadBinaries(treatment_info)
                    self.job["programs_location"] = treatment_locations

                if "control" in self.job["benchmarks"]["info"]:
                    if "programs" not in self.job["benchmarks"]["info"]["control"]:
                        getLogger().error(
                            'Field "program" must exist in '
                            'job["benchmarks"]["info"]["control"]'
                        )
                    else:
                        control_info = self.job["benchmarks"]["info"]["control"]
                        getLogger().info("Downloading control binary")
                        control_locations = self._downloadBinaries(control_info)
                        self.job["programs_location"].extend(control_locations)
        except Exception:
            raise DownloadException(
                f"Failed to download files for benchmark {self.job['identifier']} id {self.job['id']}"
            )
        finally:
            gc.collect()

    def _setStatusOutput(self, status, output):
        """Set job status and log, to be submitted to db and returned to main process"""
        if status == RUN_KILLED:
            self.job["status"] = "KILLED"
        elif status == RUN_TIMEOUT:
            self.job["status"] = "TIMEOUT"
        elif status == SUCCESS:
            self.job["status"] = "DONE"
        elif status == USER_ERROR:
            self.job["status"] = "USER_ERROR"
        else:
            self.job["status"] = "FAILED"
        if not output:
            getLogger().error("Error, output are None")
        else:
            output = trimLog(output)
            self.job["log"] = output

    def _submitDone(self):
        """Collect benchmark data and log, submit to db."""
        data = self._collectBenchmarkData(self.tempdir)
        log = collectLogData(self.job)
        self.db.doneBenchmarks(str(self.job["id"]), self.job["status"], data, log)

    def _removeBenchmarkFiles(self):
        """Attempt to remove temporary files, ignore errors."""
        shutil.rmtree(self.tempdir, True)
        programs_location = self.job.get("programs_location", [])
        for program_location in programs_location:
            shutil.rmtree(os.path.dirname(program_location), True)

        # We don't delete files from models_location because after each run
        # to save model re-download time. This might be a problem to have
        # many files saving on the disk and many disk spaces used.
        # models_location = self.job.get("models_location", [])
        # for model_location in models_location:
        #     shutil.rmtree(os.path.dirname(model_location), True)

    def _collectBenchmarkData(self, output_dir):
        data = {}
        dirs = self._listdirs(output_dir)
        for d in dirs:
            f = os.path.join(*[output_dir, d, "data.txt"])
            if not os.path.isfile(f):
                getLogger().error("The output {} doesn't exist".format(f))
                continue
            with open(f, "r") as file:
                content = json.load(file)
                # special case for power metrics
                if "power_data" in content:
                    content["power_data"] = self._handlePowerData(content["power_data"])
                data[d] = content
        return json.dumps(data)

    def _listdirs(self, path):
        return [x for x in os.listdir(path) if os.path.isdir(os.path.join(path, x))]

    def _handlePowerData(self, filename):
        if not os.path.isfile(filename):
            getLogger().error("Power data file " "{} doesn't exist".format(filename))
            return
        app = UploadDownloadFiles(self.args)
        file_link = app.upload(file=filename, permanent=False)
        # remove the temporary file
        os.remove(filename)
        return file_link

    def didUserRequestJobKill(self):
        jobs = self.db.statusBenchmarks(self.job["identifier"])
        for job in jobs:
            if job["status"] == "KILLED":
                return True
        return False

    def killJob(self):
        setRunKilled(True)


class RunLab(object):
    def __init__(self, raw_args=None):
        self.args, self.unknowns = parser.parse_known_args(raw_args)
        os.environ["CLAIMER"] = self.args.claimer_id
        self.benchmark_downloader = DownloadBenchmarks(self.args, getLogger())
        self.adb = ADB(None, self.args.android_dir)
        setLoggerLevel(self.args.logger_level)
        if not self.args.benchmark_db_entry:
            assert (
                self.args.server_addr is not None
            ), "Either server_addr or benchmark_db_entry must be specified"
            while self.args.server_addr[-1] == "/":
                self.args.server_addr = self.args.server_addr[:-1]
            self.args.benchmark_db_entry = self.args.server_addr + "/benchmark/"
        self.db = DBDriver(
            self.args.benchmark_db,
            self.args.app_id,
            self.args.token,
            self.args.benchmark_table,
            self.args.job_queue,
            self.args.test,
            self.args.benchmark_db_entry,
        )
        self.device_manager = DeviceManager(self.args, self.db)
        self.devices = self.device_manager.getLabDevices()

        if self.args.platform.startswith("host"):
            numProcesses = 2
        else:
            numProcesses = multiprocessing.cpu_count() - 1
        self.pool = Pool(max_workers=numProcesses, initializer=hookSignals)

    def run(self):
        hookSignals()
        while not stopRun(self.args):
            with LOCK:
                self._runOnce()
            time.sleep(1)
        self.db.updateDevices(self.args.claimer_id, "", True)
        self.device_manager.shutdown()

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
        # get available devices with their hashes
        devices = []
        hashes = []
        for k in self.devices:
            for hash in self.devices[k]:
                if self.devices[k][hash]["available"]:
                    devices.append(k)
                    hashes.append(hash)
        hashes = ",".join(hashes)
        devices = ",".join(devices)
        jobs = []
        if len(devices) > 0:
            jobs = self.db.claimBenchmarks(claimer_id, devices, hashes)
        return jobs

    def _selectBenchmarks(self, jobs):
        remaining_jobs = []
        jobs_queue = []
        for job in jobs:
            device_kind = job["device"]
            if device_kind not in self.devices:
                getLogger().error(
                    "Retrieved job for device "
                    f"{device_kind} cannot be run on server "
                    f"{self.args.claimer_id}."
                )
                remaining_jobs.append(job)
            elif (
                job.get("hash") is not None
                and job.get("hash") not in self.devices[device_kind]
            ):
                getLogger().error(
                    "Retrieved job for device with hash"
                    f"{job.get('hash')} cannot be run on server "
                    f"{self.args.claimer_id}."
                )
                remaining_jobs.append(job)
            else:
                if job.get("hash") is not None:
                    getLogger().info(
                        f"Job {job['id']} requests device {job['device']} with hash {job['hash']}."
                    )
                    hashes = [job["hash"]]
                else:
                    hashes = self.devices[device_kind]
                for hash in hashes:
                    device = self.devices[device_kind][hash]
                    if device["available"] is True:
                        getLogger().info(
                            f"Device {job['device']} with hash {hash} available for job {job['id']}"
                        )
                        job["hash"] = hash
                        jobs_queue.append(job)
                        device["available"] = False
                        break
                else:
                    getLogger().critical(
                        f"The requested device {job['device']} with hash {job.get('hash', '<unspecified>')}is not available on this server."
                    )
                    remaining_jobs.append(job)
        return jobs_queue, remaining_jobs

    def _releaseBenchmarks(self, remaining_jobs):
        # releasing unmatched jobs
        releasing_ids = ",".join([str(job["id"]) for job in remaining_jobs])
        self.db.releaseBenchmarks(self.args.claimer_id, releasing_ids)

    def _runBenchmarks(self, jobs_queue):
        """Given a queue of jobs, update run statuses and device statuses in db, and spawn job processes."""
        run_ids = ",".join([str(job["id"]) for job in jobs_queue])
        self.db.runBenchmarks(self.args.claimer_id, run_ids)
        run_devices = [self.devices[job["device"]][job["hash"]] for job in jobs_queue]
        getLogger().info("Updating devices status")
        self.db.updateDevices(
            self.args.claimer_id, getDevicesString(run_devices), False
        )

        # run the benchmarks
        for job in jobs_queue:
            getLogger().info(
                f"Running job with identifier {job['identifier']} and id {job['id']}"
            )
            device = self.devices[job["device"]][job["hash"]]
            device["start_time"] = time.ctime()
            async_runner = runAsync(
                self.args,
                device,
                self.db,
                job,
                self.benchmark_downloader,
                self.device_manager.usb_controller,
            )

            # Watchdog will be used to kill currently running jobs
            # based on user requests
            app = WatchDog(
                async_runner, async_runner.didUserRequestJobKill, async_runner.killJob
            )

            global RUNNING_JOBS
            RUNNING_JOBS += 1

            """
            Python's multiprocessing need to pickle things to sling them
            in different processes. However, bounded methods are not pickable,
            so the way it's doing it here doesn't work.
            Thus, I added __call__ method to the class we are passing into the
            apply_async method.
            Ref: https://stackoverflow.com/a/6975654
            """
            future = self.pool.submit(app)
            future.add_done_callback(self.callback)

    def callback(self, future_result_dict):
        """Decrement running jobs count, output job log, and start device cooldown."""
        global RUNNING_JOBS
        RUNNING_JOBS -= 1
        try:
            result = future_result_dict.result()
            job = result["job"]
            device = result["device"]
            device = self.devices[device["kind"]][device["hash"]]

            # output benchmark log in main thread.
            getLogger().info(
                "\n{}\n\nBenchmark:\t\t{}\nJob:\t\t\t{}\nDevice Kind:\t\t{}\nDevice Hash:\t\t{}\n{}\n\n{}".format(
                    "#" * 80,
                    job["identifier"],
                    job["id"],
                    device["kind"],
                    device["hash"],
                    job["log"],
                    "#" * 80,
                )
            )
        except Exception:
            getLogger().critical(
                "Couldn't complete async job. Exception from subprocess:", exc_info=True
            )

        with LOCK:
            self._coolDown(device, force_reboot=job["status"] != "DONE")

    def _coolDown(self, device, force_reboot=False):
        t = CoolDownDevice(device, self.args, self.db, force_reboot, LOCK)
        t.start()


if __name__ == "__main__":
    raw_args = None
    app = RunLab(raw_args=raw_args)
    app.run()
