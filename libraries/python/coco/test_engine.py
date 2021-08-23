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
import logging
import os
import pickle
import sys

import numpy as np
from json_dataset import JsonDataset
from json_dataset_evaluator import evaluateBoxes, evaluateMasks

FORMAT = "%(levelname)s %(asctime)s %(filename)s:%(lineno)4d: %(message)s"
logging.basicConfig(
    level=logging.ERROR, format=FORMAT, datefmt="%H:%M:%S", stream=sys.stdout
)
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="Test the result")

parser.add_argument(
    "--dataset", type=str, required=True, help="Name of the test JsonDataset"
)
parser.add_argument("--dataset_dir", type=str, required=True, help="Dataet image path")
parser.add_argument(
    "--dataset_ann", type=str, required=True, help="Dataet annotation file"
)
parser.add_argument(
    "--limit-files",
    type=int,
    required=True,
    help="The number of test files to evaluate.",
)
parser.add_argument(
    "--input-dir", type=str, required=True, help="Input directory of the results"
)
parser.add_argument(
    "--output-dir",
    type=str,
    required=True,
    help="The output directory to write the final result.",
)
parser.add_argument(
    "--result-prefix", type=str, required=True, help="The prefix of the result file"
)
parser.add_argument(
    "--total-num", type=int, required=True, help="The total number of images"
)


class TestEngine(object):
    def __init__(self, args):
        self.args = args
        self.ds = JsonDataset(args)
        self.all_results = self.emptyResults(self.ds.num_classes, args.total_num)
        self.all_boxes = self.all_results["all_boxes"]
        self.all_segms = self.all_results["all_segms"]
        self.index = 0

    def emptyResults(self, num_classes, num_images):
        # all detections are collected into:
        #    all_boxes[cls][image] = N x 5 array of detections in
        #    (x1, y1, x2, y2, score)
        ret = {
            "all_boxes": [[[] for _ in range(num_images)] for _ in range(num_classes)]
        }
        ret["all_segms"] = [[[] for _ in range(num_images)] for _ in range(num_classes)]
        return ret

    def extendResults(self, index, all_res, im_res):
        for j in range(1, len(im_res)):
            all_res[j][index] = im_res[j]

    def extendResultsWithClasses(self, index, all_boxes, box_ids):
        boxes, classids = box_ids
        for j, classid in enumerate(classids):
            classid = int(classid)
            assert classid <= len(
                all_boxes
            ), "{} classid out of range!" "class id: {}, boxes: {}".format(
                j, classid, boxes
            )
            if type(all_boxes[classid][index]) is np.ndarray:
                all_boxes[classid][index] = np.vstack(
                    (all_boxes[classid][index], boxes[j])
                )
            else:
                all_boxes[classid][index] = np.array([boxes[j]])

    def extendSegResultsWithClasses(self, index, all_segms, segs_ids):
        im_masks_rle, classids = segs_ids
        for j, classid in enumerate(classids):
            classid = int(classid)
            assert classid <= len(
                all_segms
            ), "{} classid out of range!" "class id: {}, segms: {}".format(
                j, classid, im_masks_rle
            )
            all_segms[classid][index].append(im_masks_rle[j])

    def evaluateResults(self):
        for i in range(self.args.limit_files):
            filename = os.path.join(
                self.args.input_dir, self.args.result_prefix + "_" + str(i) + ".pkl"
            )
            with open(filename, "r") as f:
                results = pickle.load(f)
            for ret in results:
                self.extendResultsWithClasses(
                    self.index, self.all_boxes, (ret["boxes"], ret["classids"])
                )
                self.extendSegResultsWithClasses(
                    self.index, self.all_segms, (ret["im_masks"], ret["classids"])
                )
                self.index = self.index + 1

    def aggregateResults(self):
        if not os.path.exists(self.args.output_dir):
            os.makedirs(self.args.output_dir)

        # evaluate results
        logger.info("Evaluating detections")
        evaluateBoxes(self.ds, self.all_boxes, self.args.output_dir, use_salt=False)

        logger.info("Evaluating segmentations")
        evaluateMasks(
            self.ds,
            self.all_boxes,
            self.all_segms,
            self.args.output_dir,
            use_salt=False,
        )

    def run(self):
        self.evaluateResults()
        self.aggregateResults()


if __name__ == "__main__":
    args = parser.parse_args()
    app = TestEngine(args)
    app.run()
