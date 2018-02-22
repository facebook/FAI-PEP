#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from utils.arg_parse import getArgs
from reporters.reporter_base import ReporterBase
from utils.custom_logger import getLogger

import json
import requests


class RemoteReporter(ReporterBase):
    def __init__(self):
        super(RemoteReporter, self).__init__()

    def report(self, content):
        if not getArgs().remote_reporter:
            return
        access_token = getArgs().remote_access_token
        remote = self._getRemoteInfo()
        logs = self._composeMessages(content, remote['category'])

        self._log(remote['url'], access_token, logs)

    def _merge_dicts(self, *dict_args):
        """
        Given any number of dicts, shallow copy and merge into a new dict,
        precedence goes to key value pairs in latter dicts.
        """
        result = {}
        for dictionary in dict_args:
            result.update(dictionary)
        return result

    def _getRemoteInfo(self):
        endpoint = getArgs().remote_reporter.strip().split("|")
        assert len(endpoint) == 2, "Category not speied in remote endpoint"
        res = {}
        res['url'] = endpoint[0].strip()
        if len(res['url']) < 5 or res['url'][:4] != 'http':
            res['url'] = 'https://' + res['url']
        res['category'] = endpoint[1].strip()

        return res

    def _composeMessages(self, content, category):
        logs = []
        meta = content[self.META].copy()
        meta["command"] = meta["command_str"]
        del meta["command_str"]
        base_summary = {}
        self._convertToInt(meta, base_summary, 'time')
        self._convertToInt(meta, base_summary, 'commit_time')
        self._convertToInt(meta, base_summary, 'control_time')
        self._convertToInt(meta, base_summary, 'control_commit_time')
        self._convertToInt(meta, base_summary, 'regression_direction')

        for item in content[self.DATA]:
            data = content[self.DATA][item]
            new_meta = meta.copy()
            new_meta['type'] = data['type']
            summary = base_summary.copy()
            self._updateSummaryData(data['summary'], summary, "")
            if 'control_summary' in data:
                self._updateSummaryData(data['control_summary'],
                                        summary, "control_")
            if 'diff_summary' in data:
                self._updateSummaryData(data['diff_summary'], summary, "diff_")
            if 'regressed' in data:
                summary['regressed'] = data['regressed']
            message = {
                'int': summary,
                'normal': new_meta,
                'normvector': {},
            }
            if 'values' in data:
                message['normvector']['values'] = data['values']
            if 'control_values' in data:
                message['normvector']['control_values'] = \
                    data['control_values']

            message_string = json.dumps(message, sort_keys=True)
            log = {
                'category': category,
                'message': message_string,
                # This allows double quotes, back slashes, etc.
                # to work correctly.
                'line_escape': False,

            }
            logs.append(log)
        return logs

    def _convertToInt(self, meta, summary, key):
        if key in meta:
            value = int(meta[key])
            meta.pop(key, None)
            summary[key] = value

    def _updateSummaryData(self, data, summary, prefix):
        for k in data:
            summary[prefix + k] = int(data[k] * 1000)

    def _log(self, url, access_token, logs):
        num_logs = len(logs)
        logs_string = json.dumps(logs, sort_keys=True)
        parameters = {
            'access_token': access_token,
            'logs': logs_string,
        }
        request = requests.post(url, json=parameters)
        result = request.json()
        count_key = 'count'
        is_good = request.ok and \
            count_key in result and \
            result[count_key] == num_logs
        if not is_good:
            getLogger().error("Submit data to remote server failed")
            if not request.ok:
                getLogger().error("Request is not okay")
            elif count_key not in result:
                getLogger().error(
                    "%s is not in request return value", count_key)
            else:
                getLogger().error(
                    "Sent %d records out of a total of %d",
                    result[count_key], num_logs)
        else:
            getLogger().info(
                "Sent %d records to remote server %s successfully.",
                num_logs, url)
        return is_good
