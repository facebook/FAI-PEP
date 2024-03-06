import argparse

import Monsoon.HVPM as HVPM
import Monsoon.pmapi as pmapi
import Monsoon.sampleEngine as sampleEngine


def testHVPM(HVMON, serialno, Protocol, power_up_current_limit, runtime_current_limit):
    HVMON.setup_usb(serialno, Protocol)
    print("HVPM Serial Number: " + repr(HVMON.getSerialNumber()))
    HVMON.setPowerUpCurrentLimit(power_up_current_limit)
    HVMON.setRunTimeCurrentLimit(runtime_current_limit)
    HVMON.fillStatusPacket()
    HVMON.setVout(4)
    HVengine = sampleEngine.SampleEngine(HVMON)
    # Output to CSV
    # Turning off periodic console outputs.
    HVengine.ConsoleOutput(True)

    # Setting all channels enabled
    HVengine.enableChannel(sampleEngine.channels.MainCurrent)
    HVengine.enableChannel(sampleEngine.channels.MainVoltage)

    # Setting trigger conditions
    # numSamples=sampleEngine.triggers.SAMPLECOUNT_INFINITE
    numSamples = 100

    HVengine.setStartTrigger(sampleEngine.triggers.GREATER_THAN, 0)
    HVengine.setStopTrigger(sampleEngine.triggers.GREATER_THAN, 60)
    HVengine.setTriggerChannel(sampleEngine.channels.timeStamp)

    # Actually start collecting samples
    HVengine.startSampling(numSamples, 1)

    print("dacCalHigh: ", HVMON.statusPacket.dacCalHigh)
    print("dacCalLow: ", HVMON.statusPacket.dacCalLow)
    print("powerupCurrentLimit: ", HVMON.statusPacket.powerupCurrentLimit)
    print("runtimeCurrentLimit: ", HVMON.statusPacket.runtimeCurrentLimit)
    print("serialNumber: ", HVMON.statusPacket.serialNumber)
    HVMON.closeDevice()


def main():
    HVMON = HVPM.Monsoon()
    available_devices = HVMON.enumerateDevices()
    parser = argparse.ArgumentParser(description="Test HVPM")
    parser.add_argument(
        "-s",
        "--serial",
        help=f"Serial number of HVPM. Available serial numbers: {available_devices}. Defaults to the first available device in this list.",
    )
    parser.add_argument(
        "-P",
        "--power_up_current_limit",
        help="Call setPowerUpCurrentLimit on the HVPM in amps. Defaults to 14",
        default=14,
        type=float,
    )
    parser.add_argument(
        "-R",
        "--runtime_current_limit",
        help="Call setRunTimeCurrentLimit on the HVPM. Defaults to 14",
        default=14,
        type=float,
    )
    parser.add_argument(
        "-l",
        "--list_devices",
        help="List available Monsoon devices by serial number",
        action="store_true",
    )
    args = parser.parse_args()
    if args.list_devices:
        print(f"Available Monsoon devices: {available_devices}")
        return

    HVPMSerialNo = None
    if args.serial is None:
        HVPMSerialNo = available_devices[0]
    elif args.serial in available_devices:
        HVPMSerialNo = args.serial
    else:
        print(
            f"Serial number {args.serial} not found. Available serial numbers: {available_devices}"
        )
        return

    testHVPM(
        HVMON,
        HVPMSerialNo,
        pmapi.USB_protocol(),
        args.power_up_current_limit,
        args.runtime_current_limit,
    )
