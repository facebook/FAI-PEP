#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

# This is the script to generate the im_info blob used in MaskRCNN2Go model

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import json
import logging
import sys

import numpy as np

FORMAT = "%(levelname)s %(asctime)s %(filename)s:%(lineno)4d: %(message)s"
logging.basicConfig(
    level=logging.DEBUG, format=FORMAT, datefmt="%H:%M:%S", stream=sys.stdout
)
logger = logging.getLogger(__name__)


parser = argparse.ArgumentParser(description="Load and extract coco dataset")

parser.add_argument(
    "--batch-size",
    type=int,
    default=-1,
    help="The batch size of the input data. If less than zero, all inputs "
    "are in one batch. Otherwise, the number of inputs must be multiples "
    "of the batch size.",
)
parser.add_argument(
    "--dataset-file",
    type=str,
    required=True,
    help="The file of the dataset containing image annotations",
)
parser.add_argument(
    "--min-size",
    type=int,
    required=True,
    help="The minimum size to scale the input image.",
)
parser.add_argument(
    "--max-size",
    type=int,
    required=True,
    help="The maximum size to scale the input image.",
)
parser.add_argument(
    "--output-file",
    type=str,
    required=True,
    help="The output file containing the info for im_info blob.",
)


class ImInfo(object):
    def __init__(self, args):
        self.args = args

    def run(self):
        with open(self.args.dataset_file, "r") as f:
            imgs = [json.loads(s) for s in f.readlines()]
        batch_size = self.args.batch_size if self.args.batch_size > 0 else len(imgs)

        num_batches = len(imgs) // batch_size
        assert len(imgs) == num_batches * batch_size
        im_infos = []
        for i in range(num_batches):
            one_batch_info = []
            for j in range(i * batch_size, (i + 1) * batch_size):
                img = imgs[j]
                im_scale = self.getScale(img["height"], img["width"])
                height = int(np.round(img["height"] * im_scale))
                width = int(np.round(img["width"] * im_scale))
                assert (
                    height <= self.args.max_size
                ), "height {} is more than the max_size {}".format(
                    height, self.args.max_size
                )
                assert (
                    width <= self.args.max_size
                ), "width {} is more than the max_size {}".format(
                    width, self.args.max_size
                )
                if height < self.args.min_size or width < self.args.min_size:
                    assert height == self.args.max_size or width == self.args.max_size
                else:
                    assert height == self.args.min_size or width == self.args.min_size
                im_info = [height, width, im_scale]
                one_batch_info.append(im_info)
            im_infos.append(one_batch_info)

        with open(self.args.output_file, "w") as f:
            f.write("{}, {}\n".format(num_batches * batch_size, 3))
            for batch in im_infos:
                for im_info in batch:
                    s = ", ".join([str(s) for s in im_info])
                    f.write("{}\n".format(s))

    def getScale(self, height, width):
        min_size = self.args.min_size
        max_size = self.args.max_size
        im_min_size = height if height < width else width
        im_max_size = height if height > width else width
        im_scale = float(min_size) / float(im_min_size)
        if np.round(im_scale * im_max_size) > max_size:
            im_scale = float(max_size) / float(im_max_size)
        return im_scale


if __name__ == "__main__":
    args = parser.parse_args()
    app = ImInfo(args)
    app.run()
