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
import json

from bridge.auth import Auth
from utils.custom_logger import getLogger
from utils.utilities import requestsJson

NETWORK_TIMEOUT = 150


class DBDriver(object):
    def __init__(self, db, app_id, token, table, job_queue, is_test, benchmark_db_entry):
        self.table = table
        self.job_queue = job_queue
        auth = Auth(db, app_id, token, is_test)
        self.auth_params = auth.get_auth_params()

        assert benchmark_db_entry != "", "Database entry cannot be empty"

        self.benchmark_db_entry = benchmark_db_entry

    def submitBenchmarks(self, data, devices, identifier, user, hashes=None):
        json_data = json.dumps(data)
        params = {
            'table': self.table,
            'job_queue': self.job_queue,
            'action': 'add',
            'identifier': identifier,
            'devices': devices,
            'benchmarks': json_data,
            'user': user,
        }
        if hashes:
            params['hashes'] = hashes
        self._requestData(params)

    def claimBenchmarks(self, server_id, devices, hashes=None):
        params = {
            'table': self.table,
            'job_queue': self.job_queue,
            'action': 'claim',
            'claimer': server_id,
            'devices': devices,
        }
        if hashes:
            params['hashes'] = hashes
        result_json = self._requestData(params)
        return self._processBenchmarkResults(result_json['values'])

    def releaseBenchmarks(self, server_id, ids):
        params = {
            'table': self.table,
            'job_queue': self.job_queue,
            'action': 'release',
            'claimer': server_id,
            'ids': ids,
        }
        self._requestData(params)

    def runBenchmarks(self, server_id, ids):
        params = {
            'table': self.table,
            'job_queue': self.job_queue,
            'action': 'run',
            'claimer': server_id,
            'ids': ids,
        }
        self._requestData(params)

    def doneBenchmarks(self, id, status, result, log):
        params = {
            'table': self.table,
            'job_queue': self.job_queue,
            'action': 'done',
            'id': id,
            'status': status,
            'result': result,
            'log': log,
        }
        self._requestData(params)

    def statusBenchmarks(self, identifier):
        params = {
            'table': self.table,
            'job_queue': self.job_queue,
            'action': 'status',
            'identifier': identifier,
        }
        request_json = self._requestData(params)
        return request_json["values"]

    def updateLogBenchmarks(self, id, log):
        params = {
            'table': self.table,
            'job_queue': self.job_queue,
            'action': 'update_log',
            'id': id,
            'log': log,
        }
        request_json = self._requestData(params, retry=False)
        return request_json["status"]

    def killBenchmarks(self, identifier):
        params = {
            'table': self.table,
            'job_queue': self.job_queue,
            'action': 'kill',
            'identifier': identifier,
        }
        self._requestData(params)

    def getBenchmarks(self, ids):
        params = {
            'table': self.table,
            'job_queue': self.job_queue,
            'action': 'get',
            'ids': ids,
        }
        request_json = self._requestData(params)
        return request_json["values"]

    def updateDevices(self, server_id, devices, reset):
        params = {
            'table': self.table,
            'job_queue': self.job_queue,
            'action': 'update_devices',
            'claimer': server_id,
            'devices': devices,
        }
        if reset:
            params["reset"] = "true"
        self._requestData(params)

    def listDevices(self, job_queue):
        params = {
            'table': self.table,
            'job_queue': job_queue,
            'action': 'list_devices',
        }
        result_json = self._requestData(params)
        return result_json["values"]

    def _requestData(self, params, retry=True):
        params.update(self.auth_params)
        result_json = requestsJson(self.benchmark_db_entry,
                                   data=params, timeout=NETWORK_TIMEOUT, retry=retry)
        if "status" not in result_json or result_json['status'] != "success":
            getLogger().warning(
                "DB post failed.\tbenchmark_db_entry: {}\t params: {}".format(self.benchmark_db_entry, json.dumps(params)))
            for key in result_json:
                getLogger().error("{}: {}".format(key, result_json[key]))
            return {
                "status": "fail",
                "values": [],
            }
        else:
            return result_json
    def _processBenchmarkResults(self, result_json):
        for result in result_json:
            benchmarks = json.loads(result["benchmarks"])
            result["benchmarks"] = benchmarks
        return result_json
