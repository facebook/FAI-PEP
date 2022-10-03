# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.
import abc


driverHandles = {}


class DriverBase(object):
    def __init__(self, *args):
        self.platform = args.platform

    @abc.abstractmethod
    def getPlatforms(self, tempdir, usb_controller):
        pass

    @abc.abstractmethod
    def getDevices(self, silent=False, retry=1):
        pass

    @staticmethod
    def matchPlatformArgs(args):
        raise AssertionError("matchPlatformArgs not implemented for DriverBase")


def registerDriver(name, obj):
    global driverHandles
    driverHandles[name] = obj


def getDriverHandles():
    return driverHandles
