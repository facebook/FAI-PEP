#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

# This is a library used to map the image names with the labels
# when the images and labels are saved in the imagenet dataset hierarchy.
# Optionally the images are shuffled


import argparse
import os
import random


parser = argparse.ArgumentParser(description="Map the images with labels")

parser.add_argument(
    "--image-dir",
    required=True,
    help="The directory of the images in imagenet database format.",
)
parser.add_argument(
    "--label-file",
    required=True,
    help="The file of the labels in imagenet database format.",
)
parser.add_argument(
    "--limit-per-category",
    type=int,
    help="Limit the number of files to get from each folder.",
)
parser.add_argument(
    "--limit-files", type=int, help="Limit the total number of files to the test set."
)
parser.add_argument(
    "--output-image-file", help="The file containing the absolute path of all images."
)
parser.add_argument(
    "--output-label-file",
    required=True,
    help="The file containing the labels for the images.",
)
parser.add_argument(
    "--shuffle", action="store_true", help="Shuffle the images and labels."
)


class ImageLableMap:
    def __init__(self):
        self.args = parser.parse_args()
        assert os.path.isfile(
            self.args.label_file
        ), f"Label file {self.args.label_file} doesn't exist"
        assert os.path.isdir(
            self.args.image_dir
        ), f"Image directory {self.args.image_dir} doesn't exist"
        if self.args.output_image_file:
            output_image_dir = os.path.dirname(
                os.path.abspath(self.args.output_image_file)
            )
            if not os.path.isdir(output_image_dir):
                os.mkdir(output_image_dir)
        output_label_dir = os.path.dirname(os.path.abspath(self.args.output_label_file))
        if not os.path.isdir(output_label_dir):
            os.mkdir(output_label_dir)

    def mapImageLabels(self):
        with open(self.args.label_file) as f:
            content = f.read()
        dir_label_mapping_str = content.strip().split("\n")

        dir_label_mapping = [line.strip().split(",") for line in dir_label_mapping_str]
        all_images_map = []
        for idx in range(len(dir_label_mapping)):
            one_map = dir_label_mapping[idx]
            rel_dir = one_map[0]
            label = one_map[1]
            dir = os.path.join(os.path.abspath(self.args.image_dir), rel_dir)
            assert os.path.isdir(dir), f"image dir {dir} doesn't exist"
            files = os.listdir(dir)
            images_map = [
                {
                    "path": os.path.join(dir, filename.strip()),
                    "index": idx,
                    "label": label,
                }
                for filename in files
            ]
            if self.args.shuffle:
                random.shuffle(images_map)
            if self.args.limit_per_category:
                images_map = images_map[: self.args.limit_per_category]

            all_images_map.extend(images_map)
        if self.args.shuffle:
            random.shuffle(all_images_map)
        if self.args.limit_files:
            all_images_map = all_images_map[: self.args.limit_files]

        if self.args.output_image_file:
            with open(self.args.output_image_file, "w") as f:
                image_files = [item["path"] for item in all_images_map]
                content = "\n".join(image_files)
                f.write(content)
        with open(self.args.output_label_file, "w") as f:
            labels = [
                str(item["index"]) + "," + item["label"] + "," + item["path"]
                for item in all_images_map
            ]
            content = "\n".join(labels)
            f.write(content)
        # print(all_images_map)


if __name__ == "__main__":
    app = ImageLableMap()
    app.mapImageLabels()
