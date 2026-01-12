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

import numpy as np


parser = argparse.ArgumentParser(description="Output compare")

parser.add_argument(
    "--benchmark-output", required=True, help="The output of the benchmark."
)
parser.add_argument("--labels", required=True, help="The golden output.")
parser.add_argument(
    "--metric-keyword",
    help="The keyword prefix each metric so that the harness can parse.",
)
parser.add_argument("--result-file", help="Write the prediction result to a file.")
parser.add_argument(
    "--top",
    type=int,
    default=1,
    help="Integer indicating whether it is a top one or top five.",
)
parser.add_argument("--name", required=True, help="Specify the type of the metric.")


class OutputCompare:
    def __init__(self):
        self.args = parser.parse_args()
        assert os.path.isfile(self.args.benchmark_output), (
            f"Benchmark output file {self.args.benchmark_output} doesn't exist"
        )
        assert os.path.isfile(self.args.labels), "Labels file {} doesn't exist".format(
            self.args.labels
        )

    def getData(self, filename):
        num_entries = 0
        content_list = []
        with open(filename) as f:
            line = f.readline()
            dim_str = line
            while line != "":
                assert dim_str == line, "The dimensions do not match"
                num_entries = num_entries + 1
                dims_list = [int(dim.strip()) for dim in line.strip().split(",")]
                line = f.readline().strip()
                content_list.extend([float(entry.strip()) for entry in line.split(",")])
                line = f.readline()

        dims_list.insert(0, num_entries)
        dims = np.asarray(dims_list)
        content = np.asarray(content_list)
        data = np.reshape(content, dims)
        # reshape to two dimension array
        benchmark_data = data.reshape((-1, data.shape[-1]))
        return benchmark_data.tolist(), dims_list

    def writeOneResult(self, values, data, metric, unit):
        entry = {
            "type": self.args.name,
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
        return entry

    def writeResult(self, results):
        top = f"top{str(self.args.top)}"
        values = [item["predict"] for item in results]
        num_corrects = sum(values)
        percent = num_corrects * 100.0 / len(values)
        output = {}
        res = self.writeOneResult(
            values, num_corrects, f"number_of_{top}_corrects", "number"
        )
        output[res["type"] + "_" + res["metric"]] = res
        res = self.writeOneResult(
            values, percent, f"percent_of_{top}_corrects", "percent"
        )
        output[res["type"] + "_" + res["metric"]] = res
        if self.args.result_file:
            s = json.dumps(output, sort_keys=True, indent=2)
            with open(self.args.result_file, "w") as f:
                f.write(s)

    def compare(self):
        benchmark_data, dims_list = self.getData(self.args.benchmark_output)
        with open(self.args.labels) as f:
            content = f.read()
            golden_lines = [
                item.strip().split(",") for item in content.strip().split("\n")
            ]
        golden_data = [
            {"index": int(item[0]), "label": item[1], "path": item[2]}
            for item in golden_lines
        ]
        if len(benchmark_data) != len(golden_data):
            idx = dims_list.index(len(golden_data))
            benchmark_data = np.reshape(
                benchmark_data, (dims_list[idx], dims_list[idx + 1])
            )
        assert len(benchmark_data) == len(golden_data), (
            f"Benchmark data has {len(benchmark_data)} entries, "
            + f"but golden data has {len(golden_data)} entries"
        )

        def sort_key(elem):
            return elem["value"]

        for i in range(len(benchmark_data)):
            benchmark_one_entry = benchmark_data[i]
            golden_one_entry = golden_data[i]
            benchmark_result = [
                {
                    "index": j,
                    "value": benchmark_one_entry[j],
                }
                for j in range(len(benchmark_one_entry))
            ]

            benchmark_result.sort(reverse=True, key=sort_key)
            golden_one_entry["predict"] = (
                1
                if golden_one_entry["index"]
                in [item["index"] for item in benchmark_result[: self.args.top]]
                else 0
            )

        self.writeResult(golden_data)


if __name__ == "__main__":
    app = OutputCompare()
    app.compare()
