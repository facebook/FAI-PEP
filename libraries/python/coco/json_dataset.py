#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

# This is the library to load the coco dataset


import argparse
import copy
import json
import logging
import os
import sys

import matplotlib

# Use a non-interactive backend
matplotlib.use("Agg")
from pycocotools.coco import COCO

FORMAT = "%(levelname)s %(asctime)s %(filename)s:%(lineno)4d: %(message)s"
logging.basicConfig(
    level=logging.DEBUG, format=FORMAT, datefmt="%H:%M:%S", stream=sys.stdout
)
logger = logging.getLogger(__name__)


IM_DIR = "image_directory"
ANN_FN = "annotation_file"
IM_PREFIX = "image_prefix"

parser = argparse.ArgumentParser(description="Load and extract coco dataset")

parser.add_argument(
    "--dataset", type=str, required=True, help="Name of the test JsonDataset"
)
parser.add_argument("--dataset_dir", type=str, required=True, help="Dataet image path")
parser.add_argument(
    "--dataset_ann", type=str, required=True, help="Dataet annotation file"
)
parser.add_argument(
    "--output-file",
    type=str,
    required=True,
    help="The file containing the loaded coco database.",
)
parser.add_argument(
    "--output-image-file",
    type=str,
    help="The file containing the image paths in the database.",
)


class JsonDataset:
    def __init__(self, args):
        self.args = args
        name = args.dataset
        ds_im_dir = args.dataset_dir
        ds_ann = args.dataset_ann
        full_datasets = {}
        if ds_im_dir is not None and ds_ann is not None:
            full_datasets[name] = {
                IM_DIR: ds_im_dir,
                ANN_FN: ds_ann,
            }
        assert name in full_datasets.keys(), f"Unknown dataset name {name}"
        logger.debug(f"Creating: {name}")

        dataset = full_datasets[name]
        logger.info(f"Loading dataset {name}:\n{dataset}")

        self.name = name
        self.image_directory = dataset[IM_DIR]
        self.image_prefix = dataset.get(IM_PREFIX, "")

        # general dataset
        self.COCO = COCO(dataset[ANN_FN])
        logger.info(f"Dataset={name}, Number of images={len(self.COCO.getImgIds())}")

        category_ids = self.COCO.getCatIds()
        categories = [c["name"] for c in self.COCO.loadCats(category_ids)]
        self.category_ids = category_ids
        self.category_to_id_map = dict(zip(categories, category_ids))
        self.classes = ["__background__"] + categories
        self.num_classes = len(self.classes)
        self.json_category_id_to_contiguous_id = {
            v: i + 1 for i, v in enumerate(self.COCO.getCatIds())
        }
        self.contiguous_category_id_to_json_id = {
            v: k for k, v in self.json_category_id_to_contiguous_id.items()
        }

    def write_roidb(self):
        coco = self.COCO
        image_ids = self.COCO.getImgIds()
        image_ids.sort()

        roidb = copy.deepcopy(coco.loadImgs(image_ids))
        for entry in roidb:
            self._prep_roidb_entry(entry)
        with open(self.args.output_file, "w") as f:
            for entry in roidb:
                s = json.dumps(entry)
                f.write(s + "\n")
        if self.args.output_image_file:
            with open(self.args.output_image_file, "w") as f:
                for entry in roidb:
                    f.write(entry["image"] + "\n")

    def _prep_roidb_entry(self, entry):
        # Reference back to the parent dataset
        # entry["dataset"] = self
        # Make file_name an abs path
        entry["image"] = os.path.join(
            os.path.abspath(self.image_directory),
            self.image_prefix + entry["file_name"],
        )

        # Remove unwanted fields if they exist
        for k in ["date_captured", "license", "file_name"]:
            if k in entry:
                del entry[k]


if __name__ == "__main__":
    args = parser.parse_args()
    app = JsonDataset(args)
    app.write_roidb()
