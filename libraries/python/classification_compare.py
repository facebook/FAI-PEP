#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

# this library is to compare the output of the benchmark and the golden output
# for image classification tasks, if the golden is 1, expecting the benchmark
# is the closest to that.


import argparse
import json
import os


parser = argparse.ArgumentParser(description="Output compare")

parser.add_argument("--benchmark-output", required=True,
    help="The output of the benchmark.")
parser.add_argument("--labels", required=True,
    help="The golden output.")
parser.add_argument("--metric-keyword",
    help="The keyword prefix each metric so that the harness can parse.")
parser.add_argument("--result-file",
    help="Write the prediction result to a file for debugging purpose.")
parser.add_argument("--top", type=int, default=1,
    help="Integer indicating whether it is a top one or top five.")


class OutputCompare(object):
    def __init__(self):
        self.args = parser.parse_args()
        assert os.path.isfile(self.args.benchmark_output), \
            "Benchmark output file {} doesn't exist".format(
                self.args.benchmark_output)
        assert os.path.isfile(self.args.labels), \
            "Labels file {} doesn't exist".format(
                self.args.labels)

    def getData(self, filename):
        with open(filename, "r") as f:
            content = f.read()
            batches = content.strip().split('\n')
        # separate out for debugging purpose
        '''
        data = []
        for batch in batches:
            one_batch = batch.strip().split(',')
            print(batch)
            import pdb; pdb.set_trace()
            one_data = []
            for item in one_batch:
                print(item + " <--")
                one_data.append(float(item.strip()))
            data.append(one_data)
        '''
        data = [[float(item) for item in batch.strip().split(',')]
                for batch in batches]
        return data

    def writeOneResult(self, values, data, metric, unit):
        entry = {
            "type": "model",
            "values": values,
            "summary": {
                "num_runs": len(values),
                "p0": data,
                "p10": data,
                "p50": data,
                "p90": data,
                "p100": data,
                "mean": data,
            },
            "unit": unit,
            "metric": metric,
        }
        s = json.dumps(entry, sort_keys=True)
        if self.args.metric_keyword:
            s = self.args.metric_keyword + " " + s
        print(s)

    def writeResult(self, results):
        values = [item["predict"] for item in results]
        num_corrects = sum(values)
        percent = num_corrects * 1. / len(values)
        self.writeOneResult(values, num_corrects,
                            "number of corrects", "number")
        self.writeOneResult(values, percent,
                            "percent of corrects", "percent")

    def compare(self):
        benchmark_data = self.getData(self.args.benchmark_output)
        with open(self.args.labels, "r") as f:
            content = f.read()
            golden_lines = [item.strip().split(',')
                            for item in content.strip().split('\n')]
        golden_data = [{"index": int(item[0]),
                        "label": item[1],
                        "path": item[2]} for item in golden_lines]
        assert len(benchmark_data) == len(golden_data), \
            "Benchmark data has {} entries, ".format(len(benchmark_data)) + \
            "but genden data has {} entries".format(len(golden_data))

        def sort_key(elem):
            return elem["value"]

        for i in range(len(benchmark_data)):
            benchmark_one_entry = benchmark_data[i]
            golden_one_entry = golden_data[i]
            benchmark_result = [{
                "index": j,
                "value": benchmark_one_entry[j],
            } for j in range(len(benchmark_one_entry))]

            benchmark_result.sort(reverse=True, key=sort_key)
            golden_one_entry["predict"] = 1 \
                if golden_one_entry["index"] in \
                [item["index"] for item in benchmark_result[:self.args.top]] \
                else 0

        self.writeResult(golden_data)


if __name__ == "__main__":
    app = OutputCompare()
    app.compare()
