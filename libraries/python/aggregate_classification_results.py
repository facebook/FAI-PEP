#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

# This script aggregates test results from multiple runs and form
# the final result

import argparse
import json
import os
import re


parser = argparse.ArgumentParser(description="Aggregate output results")

parser.add_argument("--dir", required=True,
    help="The directory of all the json data are saved.")
parser.add_argument("--limit", required=True, type=int,
    help="The directory of all the json data are saved.")
parser.add_argument("--metric-keyword",
    help="The keyword prefix each metric so that the harness can parse.")
parser.add_argument("--prefix", required=True,
    help="The prefix of the json data. The files are suffixed with a number "
         "and .txt")
parser.add_argument("--result-file",
    help="Write the prediction result to a file.")


class AggregateOutputs(object):
    def __init__(self):
        self.args = parser.parse_args()
        assert os.path.isdir(self.args.dir), \
            "Directory {} doesn't exist".format(self.args.dir)

    def _composeFilename(self, index):
        return os.path.join(self.args.dir,
                            self.args.prefix + "_" + str(index) + ".txt")

    def _getOneOutput(self, index):
        filename = self._composeFilename(index)
        if not os.path.isfile(filename):
            print("File {} does not exist".format(filename))
            return None
        with open(filename, "r") as f:
            content = json.load(f)
        return content

    def _collectAllOutputs(self):
        outputs = []
        for index in range(self.args.limit):
            output = self._getOneOutput(index)
            if output is not None:
                outputs.append(output)
        return outputs

    def _aggregateOutputs(self, outputs):
        results = {}
        for one_output in outputs:
            for key in one_output:
                value = one_output[key]
                if key not in results:
                    results[key] = value
                else:
                    results[key]["values"].extend(value["values"])
        pattern = re.compile("(\w+)_of_top(\d+)_corrects")
        # finally patch up the summary
        for res in results:
            one_result = results[res]
            one_result["type"] = one_result["type"]
            values = one_result["values"]
            match = pattern.match(one_result["metric"])
            if not match:
                continue
            if match.group(1) == "number":
                data = sum(values)
                one_result["summary"] = {
                    "num_runs": len(values),
                    "p0": data,
                    "p10": data,
                    "p50": data,
                    "p90": data,
                    "p100": data,
                    "mean": data,
                }
            elif match.group(1) == "percent":
                data = sum(values) * 100. / len(values)
                one_result["summary"] = {
                    "num_runs": len(values),
                    "p0": data,
                    "p10": data,
                    "p50": data,
                    "p90": data,
                    "p100": data,
                    "mean": data,
                }
            one_result["metric"] = "total_" + one_result["metric"]
            # there may be too many values, only keep the summary
            if len(values) > 200:
                del one_result["values"]
        return results

    def aggregate(self):
        outputs = self._collectAllOutputs()
        results = self._aggregateOutputs(outputs)
        for key in results:
            result = results[key]
            s = json.dumps(result, sort_keys=True)
            if self.args.metric_keyword:
                s = self.args.metric_keyword + " " + s
            print(s)
        if self.args.result_file:
            s = json.dumps(results, sort_keys=True, indent=2)
            with open(self.args.result_file, "w") as f:
                f.write(s)


if __name__ == "__main__":
    app = AggregateOutputs()
    app.aggregate()
