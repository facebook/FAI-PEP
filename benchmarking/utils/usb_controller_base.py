##############################################################################
# Copyright 2020-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
##############################################################################

# pyre-unsafe

from abc import ABC, abstractmethod


class USBControllerBase(ABC):
    """
    Abstrsct base class for software-controlled USB hubs. The class is used by the DeviceManager class to:
    1. Gather metadata on devices connected to the hub (i.e. which device is connected to which port)
    2. Attempt to reconnect devices that have been disconnected
    3. Flag and disable connections to unresponsive devices.

    The class should provide the framework the ability to retrieve metadata and control a device's connection by its hash.

    To accomplish this, we maintain an internal mapping of device hashes to their respective USB hubs and ports with the
    following format

    device_hub_map = {
        "device_hash_abc" = {
            <connection meta to be defined and consumed within the class. This should allow us to identify the hub and port to which the device is connected.>
        }
    }
    """

    @abstractmethod
    def __init__(self):
        pass

    """
    Returns a dictionary of device hashes to their respective hubs and ports. See how the device_hub_map is formatted above.
    """

    @abstractmethod
    def get_device_hub_map(self):
        pass

    """
    Attempt to establish or connect to the specified device hash.
    """

    @abstractmethod
    def connect(self, device_hash):
        pass

    """
    Attempt to disconnect from the specified device hash.
    """

    @abstractmethod
    def disconnect(self, device_hash):
        pass
