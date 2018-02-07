#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

import collections
import json
import os
import sys
import tempfile
import time
from utils.arg_parse import getArgs
from utils.custom_logger import getLogger
from utils.utilities import getCommand


class PlatformBase(object):
    # Class constant, need to change observer_reporter_print.cc
    # if the names are changed
    IDENTIFIER = 'Caffe2Observer '
    NET_NAME = 'Net Name'
    NET_DELAY = 'NET_DELAY'
    DELAYS_START = 'Delay Start'
    DELAYS_END = 'Delay End'
    DATA = 'data'
    META = 'meta'
    PLATFORM = 'platform'
    COMMIT = 'commit'

    def __init__(self):
        self.info = self._processInfo()
        self.platform = None
        self.platform_hash = None
        self.net_name = ""
        if getArgs().output:
            if getArgs().output_folder:
                self.output_dir = getArgs().output_folder
                if not os.path.isdir(self.output_dir):
                    os.mkdir(self.output_dir)
            else:
                assert getArgs().temp_dir, \
                    "When output is specified and output folder is not " \
                    "specified, the temp_dir must be specified."
                self.output_dir = tempfile.mkdtemp(
                    prefix=getArgs().temp_dir)

    def setPlatform(self, platform):
        self.platform = platform.replace(' ', '-')

    def getPlatform(self):
        return self.platform

    def runBenchmark(self, info):
        return None

    def runOnPlatform(self):
        data = None
        if getArgs().metric == "delay":
            data = self.runOnPlatformDelay()
        elif getArgs().metric == "error":
            data = self.runOnPlatformError()
        else:
            assert False, "Unknown metric %s." % getArgs().metric
        return self._adjustData(data)

    def runOnPlatformDelay(self):
        # Run on the treatment
        treatment_info = self.info['treatment']
        treatment_metric = self.runOnPlatformDelayOnePass(treatment_info)
        treatment_meta = self.collectMetaData(treatment_info)

        # Run on the control
        if 'control' in self.info:
            # wait till the device is cooler
            # time.sleep(60)
            control_info = self.info['control']
            control_metric = self.runOnPlatformDelayOnePass(control_info)
            control_meta = self.collectMetaData(control_info)
        else:
            control_meta = None
            control_metric = None

        meta = self._mergeMetaData(treatment_meta, control_meta)
        data = self._processDelayData(treatment_metric, control_metric)
        result = {}
        result[self.META] = meta
        result[self.DATA] = data
        return result

    def runOnPlatformDelayOnePass(self, info):
        results = []
        repeat = True
        while repeat:
            output = self.runBenchmark(info)
            repeat = self.collectDelayData(output, results)
        metric = self._processData(results)
        return metric

    def runOnPlatformError(self):
        # Run on the treatment
        treatment_info = self.info['treatment']

        treatment_output = self.runBenchmark(treatment_info)
        # just to get the net name
        self.collectDelayData(treatment_output, [])
        treatment_meta = self.collectMetaData(treatment_info)
        output_filenames = self._composeOutputFilenames()
        treatment_metric = self._collectErrorData(output_filenames)
        meta = self._mergeMetaData(treatment_meta, None)
        data = self._processErrorData(treatment_metric)
        result = {}
        result[self.META] = meta
        result[self.DATA] = data
        return result

    def collectMetaData(self, info):
        ts = time.time()
        meta = {}
        meta['time'] = ts
        meta['net_name'] = self.net_name if len(self.net_name) > 0 else \
            os.path.basename(getArgs().net)
        meta['metric'] = getArgs().metric
        meta['command'] = sys.argv
        meta['command_str'] = getCommand(meta['command'])
        meta[self.PLATFORM] = self.platform
        if info['commit']:
            meta[self.COMMIT] = info['commit']
        if info['commit_time']:
            meta['commit_time'] = info['commit_time']
        if getArgs().identifier:
            meta['identifier'] = getArgs().identifier
        return meta

    def collectDelayData(self, output, results):
        if output is None:
            return False
        prev_num = len(results)
        rows = output.split('\n')
        useful_rows = [row for row in rows if row.find(self.IDENTIFIER) >= 0]
        i = 0
        while (i < len(useful_rows)):
            row = useful_rows[i]
            net_start_idx = row.find(self.NET_NAME)
            if net_start_idx > 0:
                content = row[net_start_idx:].strip().split('-')
                assert len(content) == 2, \
                    "Net delay row doesn't have two items: " + row
                self.net_name = content[1].strip()
            else:
                result = {}
                if (i < len(useful_rows) and
                        (useful_rows[i].find(self.DELAYS_START) >= 0)):
                    i = self._parseDelayData(useful_rows, result, i)
                if (len(result) > 1) and (self.NET_DELAY in result):
                    # operator delay. Need to strip the net delay from it
                    del result[self.NET_DELAY]
                results.append(result)
            i += 1
        if getArgs().run_individual:
            total_num = getArgs().iter * 2
        else:
            total_num = getArgs().iter

        if len(results) > total_num:
            # Android 5 has an issue that logcat -c does not clear the entry
            results = results[-total_num:]
        elif len(results) < total_num:
            if len(results) > prev_num:
                getLogger().info(
                        "%d items collected. Still missing %d items. "
                        "Collect again." %
                        (len(results) - prev_num, total_num - len(results)))
                return True
            else:
                getLogger().info(
                        "No new items collected, finish collecting...")
        return False

    def getNameList(self, names):
        return names.strip().split(',')

    def _parseDelayData(self, rows, result, start_idx):
        assert rows[start_idx].find(self.DELAYS_START) >= 0, \
                "Does not find the start of the delay"
        i = start_idx+1
        while i < len(rows) and rows[i].find(self.DELAYS_END) < 0:
            row = rows[i]
            start_idx = row.find(self.IDENTIFIER) + len(self.IDENTIFIER)
            pair = row[start_idx:].strip().split('-')
            assert len(pair) == 2, \
                "Operator delay doesn't have two items: %s" % row
            unit_idx = pair[1].find("(")
            assert unit_idx > 0, "Unit is not specified"
            result[pair[0].strip()] = float(pair[1][:unit_idx-1].strip())
            i = i+1
        return i

    def _getStatistics(self, sorted_array):
        return {
            'p0': sorted_array[0],
            'p100': sorted_array[-1],
            'p50': self._getMedian(sorted_array),
            'p10': sorted_array[len(sorted_array) // 10],
            'p90': sorted_array[len(sorted_array) -
                                len(sorted_array) // 10 - 1],
        }

    def _processData(self, data):
        details = collections.defaultdict(list)
        for d in data:
            for k, v in d.items():
                details[k].append(v)
        processed_data = {}
        for d in details:
            details[d].sort()
            values = details[d]
            assert len(values) > 0
            processed_data[d] = {
                'values': values,
                'summary': self._getStatistics(values)
            }

        return processed_data

    def _getMedian(self, values):
        length = len(values)
        return values[length // 2] if (length % 2) == 1 else \
            (values[(length - 1) // 2] + values[length // 2]) / 2

    def _processInfo(self):
        info = None
        if getArgs().program:
            assert not getArgs().android and getArgs().host, \
                "Cannot specify both --android and " \
                "--host when --program is specified."
            info = {'treatment': {}}
            if getArgs().android or getArgs().host:
                info['treatment']['program'] = getArgs().program
            return info
        elif getArgs().info:
            info = json.loads(getArgs().info)
        else:
            assert False, \
                "Must specify either --program or --info in command line"
        assert info and info['treatment'], \
            "Treatment is not specified."
        return info

    def _mergeMetaData(self, treatment_meta, control_meta):
        meta = treatment_meta.copy()
        meta['regression_direction'] = getArgs().regression_direction
        meta['run_type'] = getArgs().run_type
        if control_meta:
            meta['control_time'] = control_meta['time']
            meta['control_commit'] = control_meta['commit']
            meta['control_commit_time'] = control_meta['commit_time']
        return meta

    def _processDelayData(self, treatment_metric, control_metric):
        data = {}
        for k in treatment_metric:
            treatment_value = treatment_metric[k]
            data[k] = treatment_value
            data[k]['type'] = k

        if not control_metric:
            return data

        for k in treatment_metric:
            # Just skip this entry if the value doesn't exist in control
            if k not in control_metric:
                getLogger().error(
                    "Value %s existed in treatment but not control" % k)
                continue
            control_value = control_metric[k]
            treatment_value = treatment_metric[k]
            for control_key in control_value:
                new_key = 'control_' + control_key
                data[k][new_key] = control_value[control_key]
            # create diff of delay
            csummary = control_value['summary']
            tsummary = treatment_value['summary']
            assert csummary is not None and tsummary is not None, \
                "The summary section in control and treatment cannot be None."
            data[k]['diff_summary'] = {
                "p0": tsummary['p0'] - csummary['p100'],
                "p50": tsummary['p50'] - csummary['p50'],
                "p100": tsummary['p100'] - csummary['p0'],
                "p10": tsummary['p10'] - csummary['p90'],
                "p90": tsummary['p90'] - csummary['p10'],
            }
        return data

    def _collectErrorData(self, output_filenames):
        outputs = self.getNameList(getArgs().output)
        assert len(outputs) == len(output_filenames), \
            "The number of files specified in output_filenames does not " \
            "match the number of outputs"
        values = {}
        for output, output_filename in zip(outputs, output_filenames):
            values[output] = self._getOutputFileValue(output_filename)
        return values

    def _composeOutputFilenames(self):
        outputs = self.getNameList(getArgs().output)
        return [self.output_dir + "/" + output + ".txt" for output in outputs]

    def _getOutputFileValue(self, output_filename):
        assert os.path.isfile(output_filename), \
            "Output file %s does not exist." % output_filename
        with open(output_filename, 'r') as file:
            content = file.read().splitlines()
            # times 1000 to give more precision
            return [float(x.strip()) * 1000 for x in content]

    def _processErrorData(self, treatment_metric):
        golden_filenames = self.getNameList(getArgs().golden_output_file)
        golden_metric = self._collectErrorData(golden_filenames)
        data = {}
        for output in treatment_metric:
            treatment_values = treatment_metric[output]
            golden_values = golden_metric[output]
            diff_values = list(map(
                lambda pair: pair[0] - pair[1],
                zip(treatment_values, golden_values)))
            diff_values.sort()
            treatment_values.sort()
            golden_values.sort()
            data[output] = {
                'summary': self._getStatistics(treatment_values),
                'control_summary': self._getStatistics(golden_values),
                'diff_summary': self._getStatistics(diff_values),
            }
            data[output]['type'] = output
        return data

    def _adjustData(self, data):
        regressed_types_string = getArgs().regressed_types
        if regressed_types_string is None:
            return data
        values = data[self.DATA]
        regressed_types = json.loads(regressed_types_string)
        if getArgs().run_type == 'regress':
            for v in values:
                if v in regressed_types:
                    values[v]['regressed'] = 1
        return data
