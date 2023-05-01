import Monsoon.HVPM as HVPM
import Monsoon.pmapi as pmapi
import Monsoon.sampleEngine as sampleEngine


def testHVPM(serialno, Protocol):
    HVMON = HVPM.Monsoon()
    HVMON.setup_usb(serialno, Protocol)
    print("HVPM Serial Number: " + repr(HVMON.getSerialNumber()))
    HVMON.setPowerUpCurrentLimit(13)
    HVMON.setRunTimeCurrentLimit(13)
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
    HVPMSerialNo = None
    testHVPM(HVPMSerialNo, pmapi.USB_protocol())


if __name__ == "__main__":
    main()
