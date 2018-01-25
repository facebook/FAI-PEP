#!/usr/bin/env python3.6

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

from regression_detectors.regression_detector_base \
    import RegressionDetectorBase
from utils.custom_logger import getLogger


class DelayRegressionDetector(RegressionDetectorBase):
    def __init__(self):
        super(DelayRegressionDetector, self).__init__()

    def isRegressed(self, filename, latest_data, compare_data,
                    control_in_compare):
        # The algorithm to check whether there is a regression
        if control_in_compare:
            return self.detectionOnMeasurement(latest_data, compare_data)
        else:
            return self.detectionOnDiff(latest_data, compare_data)

    def detectionOnDiff(self, latest_data, compare_data):
        if "diff_summary" not in latest_data or \
                not all("diff_summary" in x for x in compare_data):
            getLogger().error("Diff summary does not exist in data")
            return self.detectionOnMeasurement(latest_data, compare_data)
        return self._detectionP50vsP90(latest_data, compare_data,
                                       "diff_summary")

    def detectionOnMeasurement(self, latest_data, compare_data):
        return self._detectionP50vsP90(latest_data, compare_data, "summary")

    # There is a regression if the p50 is greater than
    # the p90 of the p90 plus the average difference of the p90s
    def _detectionP50vsP90(self, latest_data, compare_data, summary_kind):
        if len(compare_data) < 5:
            return False
        latest_p50 = latest_data[summary_kind]["p50"]
        p90s = self._getSummaryValue(compare_data,
                                     summary_kind, "p90")
        p90s.sort()
        p90_range = p90s[-1] - p90s[0]
        p90_idx = int((len(p90s) * 9) / 10)
        p90_of_p90s = p90s[p90_idx]
        return latest_p50 > (p90_of_p90s + int(p90_range / 10))

    def _getSummaryValue(self, data, summary_type, field):
        return [x[summary_type][field] for x in data]
