from __future__ import absolute_import, division, print_function, unicode_literals

import json

from .models import BenchmarkResult


def store_result(data):
    logs = json.loads(data["logs"])

    for log in logs:
        store_single_entry(log)

    return {"status": "success", "count": len(logs)}


def store_single_entry(log):
    message = json.loads(log["message"])

    r = BenchmarkResult()

    process_entry(r, message, "int")
    process_entry(r, message, "normal")
    process_vec_entry(r, message, "normvector")

    r.save()


def process_entry(r, message, type):
    for k, v in message[type].items():
        if k == "net_name":
            k = "model"
        try:
            setattr(r, k, v)
        except Exception:
            print("{} is not a valid field")


def process_vec_entry(r, message, type):
    for k, v in message[type].items():
        if k == "net_name":
            k = "model"
        v = json.dumps(v)
        try:
            setattr(r, k, v)
        except Exception:
            print("{} is not a valid field")
