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
import json
import pickle

import cv2
import numpy as np
import pycocotools.mask as mask_util


parser = argparse.ArgumentParser(description="Process the single image output")

parser.add_argument(
    "--blob-names", type=str, required=True, help="Comma separated blob names. "
)
parser.add_argument(
    "--blob-files",
    type=str,
    required=True,
    help="Comma separated blob files. The order is expected to be "
    "the same as the blob names.",
)
parser.add_argument(
    "--im-info",
    type=str,
    required=True,
    help="The file for image info. Used to get the height,width of the image",
)
parser.add_argument(
    "--output-file",
    type=str,
    required=True,
    help="The output file of the processed predictions.",
)
parser.add_argument(
    "--rle-encode", action="store_true", help="Whether to use rle encode."
)


class ProcessSingleImageOutput(object):
    def __init__(self, args):
        self.args = args

    def getData(self, filename):
        result = []
        with open(filename, "r") as f:
            line = f.readline()
            while line != "":
                content_list = []
                dims_list = [int(dim.strip()) for dim in line.strip().split(",")]
                line = f.readline().strip()
                if len(line) > 0:
                    content_list = [float(entry.strip()) for entry in line.split(",")]
                line = f.readline()
                dims = np.asarray(dims_list)
                content = np.asarray(content_list)
                data = np.reshape(content, dims)
                result.append(data)
        return result

    def getBlobs(self):
        blob_names = self.args.blob_names.split(",")
        blob_files = self.args.blob_files.split(",")
        blobs = {}
        assert len(blob_names) == len(blob_files)
        for i in range(len(blob_names)):
            blobs[blob_names[i]] = self.getData(blob_files[i])
        # restructure the blobs.
        # All blobs should have the same number of entries
        num = len(blobs[blob_names[0]])
        blob_array = []
        for i in range(num):
            one_entry = {}
            for name in blob_names:
                assert (
                    len(blobs[name]) == num
                ), "Different entries have different numbers"
                one_entry[name] = blobs[name][i]
            blob_array.append(one_entry)
        return blob_array

    def expand_boxes(self, boxes, scale):
        """Expand an array of boxes by a given scale."""
        box_dim = boxes.shape[1]
        if box_dim == 4:
            w_half = (boxes[:, 2] - boxes[:, 0]) * 0.5
            h_half = (boxes[:, 3] - boxes[:, 1]) * 0.5
            x_c = (boxes[:, 2] + boxes[:, 0]) * 0.5
            y_c = (boxes[:, 3] + boxes[:, 1]) * 0.5

            w_half *= scale
            h_half *= scale

            boxes_exp = np.zeros(boxes.shape)
            boxes_exp[:, 0] = x_c - w_half
            boxes_exp[:, 2] = x_c + w_half
            boxes_exp[:, 1] = y_c - h_half
            boxes_exp[:, 3] = y_c + h_half
        elif box_dim == 5:
            boxes_exp = boxes.copy()
            boxes_exp[:, 2:4] *= scale
        else:
            raise Exception("Unsupported box dimension: {}".format(box_dim))

        return boxes_exp

    def compute_segm_results(
        self,
        masks,
        ref_boxes,
        classids,
        im_h,
        im_w,
        thresh_binarize=0.5,
        rle_encode=True,
    ):
        """masks: (#boxes, #classes, mask_dim, mask_dim)
        ref_boxes: (#boxes, 5), where each row is [x1, y1, x2, y2, cls]
        classids: (#boxes, )
        ret: list of im_masks, [im_mask, ...] or [im_mask_rle, ...]
        """
        assert len(masks.shape) == 4
        assert masks.shape[2] == masks.shape[3]
        assert masks.shape[0] == ref_boxes.shape[0]
        assert ref_boxes.shape[1] == 4
        assert len(classids) == masks.shape[0]
        all_segms = []
        # To work around an issue with cv2.resize (it seems to automatically pad
        # with repeated border values), we manually zero-pad the masks by 1 pixel
        # prior to resizing back to the original image resolution. This prevents
        # "top hat" artifacts. We therefore need to expand the reference boxes by an
        # appropriate factor.
        M = masks.shape[2]
        scale = (M + 2.0) / M
        ref_boxes = self.expand_boxes(ref_boxes, scale)
        ref_boxes = ref_boxes.astype(np.int32)
        padded_mask = np.zeros((M + 2, M + 2), dtype=np.float32)

        for mask_ind in range(masks.shape[0]):
            cur_cls = int(classids[mask_ind])
            padded_mask[1:-1, 1:-1] = masks[mask_ind, cur_cls, :, :]

            ref_box = ref_boxes[mask_ind, :]
            w = ref_box[2] - ref_box[0] + 1
            h = ref_box[3] - ref_box[1] + 1
            w = np.maximum(w, 1)
            h = np.maximum(h, 1)

            mask = cv2.resize(padded_mask, (w, h))
            mask = np.array(mask > thresh_binarize, dtype=np.uint8)
            im_mask = np.zeros((im_h, im_w), dtype=np.uint8)

            x_0 = max(ref_box[0], 0)
            x_1 = min(ref_box[2] + 1, im_w)
            y_0 = max(ref_box[1], 0)
            y_1 = min(ref_box[3] + 1, im_h)
            im_mask[y_0:y_1, x_0:x_1] = mask[
                (y_0 - ref_box[1]) : (y_1 - ref_box[1]),
                (x_0 - ref_box[0]) : (x_1 - ref_box[0]),
            ]

            ret = im_mask
            if rle_encode:
                # Get RLE encoding used by the COCO evaluation API
                rle = mask_util.encode(np.array(im_mask[:, :, np.newaxis], order="F"))[
                    0
                ]
                ret = rle

            all_segms.append(ret)

        return all_segms

    def process(self):
        im_infos = []
        with open(self.args.im_info, "r") as f:
            lines = f.readlines()
        for line in lines:
            im_info = json.loads(line)
            im_infos.append(im_info)

        blobs = self.getBlobs()
        assert len(im_infos) == len(
            blobs
        ), "The number for im_infos and blobs do not match"
        results = []
        for i in range(len(blobs)):
            one_blob = blobs[i]
            im_info = im_infos[i]
            classids = one_blob["class_nms"]
            scores = one_blob["score_nms"]  # bbox scores, (R, )
            boxes = one_blob["bbox_nms"]  # i.e., boxes, (R, 4*1)
            masks = one_blob["mask_fcn_probs"]  # (R, cls, mask_dim, mask_dim)
            R = boxes.shape[0]
            im_masks = []
            if R > 0:
                im_masks = self.compute_segm_results(
                    masks,
                    boxes,
                    classids,
                    im_info["height"],
                    im_info["width"],
                    rle_encode=self.args.rle_encode,
                )

            boxes = np.column_stack((boxes, scores))

            ret = {
                "classids": classids,
                "boxes": boxes,
                "masks": masks,
                "im_masks": im_masks,
            }
            results.append(ret)
        with open(self.args.output_file, "w") as f:
            pickle.dump(results, f, pickle.HIGHEST_PROTOCOL)


if __name__ == "__main__":
    args = parser.parse_args()
    app = ProcessSingleImageOutput(args)
    app.process()
