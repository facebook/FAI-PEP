#!/usr/bin/env python

##############################################################################
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################


import argparse
import copy
import hashlib
import json
import logging
import os
import shutil

import requests

parser = argparse.ArgumentParser(description="Perform one benchmark run")
parser.add_argument("--model", help="Specified the model to generate the meta data.")
parser.add_argument(
    "--model_cache",
    required=True,
    help="The local directory containing the cached models. It should not "
    "be part of a git directory.",
)
parser.add_argument(
    "--specifications_dir",
    required=True,
    help="Required. The root directory that all specifications resides. "
    "Usually it is the specifications directory.",
)
parser.add_argument(
    "--overwrite_meta", action="store_true", help="Overwrite the meta data."
)


logging.basicConfig()

logger = logging.getLogger("GlobalLogger")

logger.setLevel(logging.DEBUG)

models = {
    "bvlc_alexnet": {
        "desc": "BVLC AlexNet",
        "inputs": {"data": {"shapes": [[1, 3, 224, 224]]}},
    },
    "bvlc_googlenet": {
        "desc": "BVLC GoogleNet",
        "inputs": {"data": {"shapes": [[1, 3, 224, 224]]}},
    },
    "bvlc_reference_caffenet": {
        "desc": "BVLC Reference CaffeNet",
        "inputs": {"data": {"shapes": [[1, 3, 224, 224]]}},
    },
    "bvlc_reference_rcnn_ilsvrc13": {
        "desc": "BVLC Reference RCNN ILSVRC13",
        "inputs": {"data": {"shapes": [[1, 3, 224, 224]]}},
    },
    "densenet121": {
        "desc": "121-layer DenseNet",
        "inputs": {"data": {"shapes": [[1, 3, 224, 224]]}},
    },
    "inception_v1": {
        "desc": "Inception V1",
        "inputs": {"data": {"shapes": [[1, 3, 224, 224]]}},
    },
    "inception_v2": {
        "desc": "Inception V2",
        "inputs": {"data": {"shapes": [[1, 3, 224, 224]]}},
    },
    "resnet50": {
        "desc": "50 layer ResNet",
        "inputs": {"gpu_0/data": {"shapes": [[1, 3, 224, 224]]}},
    },
    "shufflenet": {
        "desc": "ShuffleNet",
        "inputs": {"gpu_0/data": {"shapes": [[1, 3, 224, 224]]}},
    },
    "style_transfer": {
        "desc": "style transfer",
        "model_dir": "style_transfer/animals",
        "inputs": {"data_int8_bgra": {"shapes": [[1, 640, 360, 4]], "type": "uint8_t"}},
    },
    "vgg16": {
        "desc": "16 layer VGG",
        "inputs": {"gpu_0/data": {"shapes": [[1, 3, 224, 224]]}},
    },
    "vgg19": {
        "desc": "19 layer VGG",
        "inputs": {"data": {"shapes": [[1, 3, 224, 224]]}},
    },
}

json_template = {
    "model": {
        "category": "CNN",
        "description": "Trained @DESC@ on Caffe2",
        "files": {
            "init": {
                "filename": "init_net.pb",
                "location": "https://s3.amazonaws.com/download.caffe2.ai/models/@DIR@/init_net.pb",
                "md5": "",
            },
            "predict": {
                "filename": "predict_net.pb",
                "location": "https://s3.amazonaws.com/download.caffe2.ai/models/@DIR@/predict_net.pb",
                "md5": "",
            },
        },
        "format": "caffe2",
        "kind": "deployment",
        "name": "@NAME@",
    },
    "tests": [
        {
            "commands": [
                '{program} --net {files.predict} --init_net {files.init} --warmup {warmup} --iter {iter} --input "data" --input_dims "1,3,224,224" --input_type float --run_individual true'
            ],
            "identifier": "{ID}",
            "iter": 50,
            "metric": "delay",
            "warmup": 1,
        }
    ],
}


def genModelMetas(args):
    for model_name in models:
        model = models[model_name]
        genOneModelMeta(args, model_name, model)


def genOneModelMeta(args, model_name, model):
    meta = copy.deepcopy(json_template)
    model_dir = model["model_dir"] if "model_dir" in model else model_name
    desc = model["desc"]
    meta["model"]["description"] = meta["model"]["description"].replace("@DESC@", desc)
    meta["model"]["name"] = model_name

    inputs = copy.deepcopy(model["inputs"])
    for iname in inputs:
        inp = inputs[iname]
        if "type" not in inp:
            inp["type"] = "float"
    meta["tests"][0]["inputs"] = inputs

    for fname in meta["model"]["files"]:
        f = meta["model"]["files"][fname]
        f["location"] = f["location"].replace("@DIR@", model_dir)
        target = os.path.join(*[args.model_cache, "caffe2", model_name, f["filename"]])
        md5 = downloadFile(f["location"], target)
        if md5 is None:
            return
        f["md5"] = md5

    path = [args.specifications_dir, "models/caffe2", model_name, model_name + ".json"]
    filename = os.path.join(*path)

    if not os.path.isfile(filename) or args.overwrite_meta:
        if not os.path.isdir(path):
            os.makedirs(path)
        s = json.dumps(meta, indent=2, sort_keys=True)
        with open(filename, "w") as f:
            f.write(s)
        logger.info(f"Writing {filename}")


def downloadFile(location, target):
    logger.info(f"Downloading {location}")
    r = requests.get(location)
    if r.status_code == 200:
        target_dir = os.path.dirname(target)
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)
        with open(target, "wb") as f:
            f.write(r.content)
        m = hashlib.md5()
        m.update(open(target, "rb").read())
        md5 = m.hexdigest()
        fn = os.path.splitext(target)
        new_target = fn[0] + "_" + md5 + fn[1]
        shutil.move(target, new_target)
        logger.info(f"Write file {new_target}")
        return md5
    return None


if __name__ == "__main__":
    args = parser.parse_args()
    if args.model:
        if args.model in models:
            m = models[args.model]
            genOneModelMeta(args, args.model, m)
        else:
            logger.error(f"Model {args.model} is not specified")
    else:
        genModelMetas(args)
