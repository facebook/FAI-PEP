##############################################################################
# Copyright 2022-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

# pyre-unsafe

counter_handles = {}


class Counter:
    def __init__(self, context: str = "default"):
        self.counter_handles = get_counter_handles()
        if context not in self.counter_handles:
            raise RuntimeError(f"No configuration found for {context}")
        self.counter = self.counter_handles[context]()

    def update_counters(self, data: list[dict]):
        return self.counter.update_counters(data)

    def get_counter(self):
        return self.counter


def register_counter_handle(name, obj):
    global counter_handles
    counter_handles[name] = obj


def get_counter_handles():
    return counter_handles
