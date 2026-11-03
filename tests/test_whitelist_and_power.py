import os
import pytest
from Backend.DetectHardware import DetectHardware
from GUI.AppGUI import getAcPowerStatus, watchdogCommand, HEARTBEAT_FILE

def test_hardware_whitelist():
    assert DetectHardware.isSupportedModel("Dell Inc. Dell G15 5530")
    assert DetectHardware.isSupportedModel("Dell Inc. Dell G15 5520")
    assert not DetectHardware.isSupportedModel("Dell Inc. XPS 13 9310")
    assert not DetectHardware.isSupportedModel("Alienware m16")
    assert not DetectHardware.isSupportedModel(None)


def test_hardware_whitelist_env_override():
    os.environ.pop("TCC_ALLOW_UNSUPPORTED", None)
    assert DetectHardware.isUnsupportedAllowed() is False
    
    os.environ["TCC_ALLOW_UNSUPPORTED"] = "1"
    assert DetectHardware.isUnsupportedAllowed() is True
    
    os.environ.pop("TCC_ALLOW_UNSUPPORTED", None)


def test_watchdog_command_structure():
    cmd = watchdogCommand(HEARTBEAT_FILE)
    assert cmd is not None
    assert cmd[-1] == HEARTBEAT_FILE
    target = cmd[1] if len(cmd) > 2 else cmd[0]
    assert os.path.exists(target)


def test_power_status_query():
    status = getAcPowerStatus()
    # On Windows running on hardware, returns True (AC) or False (Battery)
    assert status in (True, False, None)
