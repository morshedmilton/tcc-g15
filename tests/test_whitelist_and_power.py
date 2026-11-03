import os
import pytest
from Backend.DetectHardware import DetectHardware
from GUI.AppGUI import getAcPowerStatus, watchdogCommand, HEARTBEAT_FILE

def test_hardware_whitelist():
    assert DetectHardware.isSupportedModel("Dell Inc. Dell G15 5530")
    assert DetectHardware.isSupportedModel("Dell Inc. Dell G15 5520")
    assert DetectHardware.isSupportedModel("Dell Inc. Dell G16 7630")
    assert DetectHardware.isSupportedModel("Alienware m15 R7")
    assert DetectHardware.isSupportedModel("Alienware m16 R1")
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


def test_watchdog_resurrection(qapp):
    """Test that GUI automatically resurrects a terminated watchdog process."""
    from unittest.mock import MagicMock, patch
    from GUI.AppGUI import TCC_GUI
    from GUI.HotKey import HotKey

    orig_hotkey = HotKey.start
    HotKey.start = lambda self: None
    orig_watchdog = TCC_GUI._startWatchdog
    TCC_GUI._startWatchdog = lambda self: None

    try:
        awcc = MagicMock()
        awcc.GPUFanIdx = 0
        awcc.CPUFanIdx = 1
        awcc.Mode.Balanced = 1
        awcc.setMode.return_value = True
        awcc.getFanRelatedTemp.return_value = 50
        awcc.getFanRPM.return_value = 2000

        with patch('GUI.AppGUI.DetectHardware') as mock_dh:
            mock_dh.return_value.getHardwareName.return_value = 'Test Device'
            window = TCC_GUI(awcc)

            # Mock an active watchdog process
            mock_proc = MagicMock()
            mock_proc.poll.return_value = None  # None means process is still running
            window._watchdog = mock_proc
            assert window._isWatchdogAlive() is True

            # Mock watchdog process termination (e.g. exit code 0)
            mock_proc.poll.return_value = 0
            assert window._isWatchdogAlive() is False

            # Verify ensureWatchdogRunning resurrects the watchdog
            start_mock = MagicMock()
            window._startWatchdog = start_mock
            window._ensureWatchdogRunning()
            start_mock.assert_called_once()

            # Verify that if app is shutting down, watchdog is NOT resurrected
            start_mock.reset_mock()
            window._watchdogShuttingDown = True
            window._ensureWatchdogRunning()
            start_mock.assert_not_called()
    finally:
        HotKey.start = orig_hotkey
        TCC_GUI._startWatchdog = orig_watchdog
