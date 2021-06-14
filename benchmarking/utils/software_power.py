from __future__ import absolute_import, division, print_function, unicode_literals

import time

from utils.custom_logger import getLogger


class PowerUtil:
    def __init__(self, platform, duration):
        self.platform = platform
        self.data = []
        self.duration = duration

    def collect(self):
        self.data.append(self.platform.currentPower())
        self.platform.usb_controller.disconnect(self.platform.platform_hash)

        getLogger().info("Sleeping for {}".format(self.duration))
        time.sleep(self.duration)

        self.platform.usb_controller.connect(self.platform.platform_hash)
        time.sleep(2) # device needs a second to connect
        self.data.append(self.platform.currentPower())

        getLogger().info("Done collecting {}".format(self.data))
        result = {}
        result["software_power"] = _composeStructuredData(
            self.data,
            self.platform.powerInfo["metric"],
            self.platform.powerInfo["unit"]
        )
        return result


def _composeStructuredData(data, metric, unit):
    # TODO(axit): Fix the structure based on how we want to display battery data
    def _index(percentile):
        return int(percentile/100.0 * len(data)) - 1
    return {
        "values": data,
        "type": "NET",
        "metric": metric,
        "unit": unit,
        "summary": {
            "p0": data[0],
            "p10": data[_index(10)],
            "p50": data[_index(50)],
            "p90": data[_index(90)],
            "p100": data[_index(100)],
            "mean": 0,
            "stdev": 0,
            "MAD": 0,
        }
    }
