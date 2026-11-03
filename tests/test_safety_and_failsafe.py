import time
from unittest.mock import MagicMock, patch
import pytest
from GUI.HotKey import HotKey
from GUI.AppGUI import TCC_GUI, ThermalMode, MODE_ORDER

def test_temperature_sanity_filter():
    # Bogus Dell WMI 2-3°C bug readings must be discarded
    assert TCC_GUI._saneTemp(2) is None
    assert TCC_GUI._saneTemp(3) is None
    assert TCC_GUI._saneTemp(4) is None
    assert TCC_GUI._saneTemp(None) is None
    assert TCC_GUI._saneTemp(121) is None
    assert TCC_GUI._saneTemp(-10) is None
    
    # Valid readings
    assert TCC_GUI._saneTemp(5) == 5
    assert TCC_GUI._saneTemp(55) == 55
    assert TCC_GUI._saneTemp(85) == 85
    assert TCC_GUI._saneTemp(100) == 100
    assert TCC_GUI._saneTemp(120) == 120


def test_mode_order_contains_all_five_modes():
    mode_names = [m.name for m in MODE_ORDER]
    expected = ["Custom", "Balanced", "Performance", "Quiet", "G_Mode"]
    assert mode_names == expected


def test_failsafe_constants():
    assert TCC_GUI.FAILSAFE_CPU_TEMP == 95
    assert TCC_GUI.FAILSAFE_GPU_TEMP == 85
    assert TCC_GUI.FAILSAFE_HARD_CPU_TEMP == 100
    assert TCC_GUI.FAILSAFE_HARD_GPU_TEMP == 90
    assert TCC_GUI.FAILSAFE_TRIGGER_DELAY_SEC == 8
    assert TCC_GUI.FAILSAFE_HARD_TRIGGER_DELAY_SEC == 4
    assert TCC_GUI.FAILSAFE_RESET_AFTER_TEMP_IS_OK_FOR_SEC == 60


def test_inv1_hard_failsafe_unbypassable(qapp):
    """INV-1 Invariant Test: Hard emergency trip (CPU >= 100°C) must force G_Mode

    even if user has explicitly turned the soft fail-safe toggle OFF.
    """
    orig_hotkey = HotKey.start
    HotKey.start = lambda self: None
    orig_watchdog = TCC_GUI._startWatchdog
    TCC_GUI._startWatchdog = lambda self: None

    try:
        awcc = MagicMock()
        awcc.GPUFanIdx = 0
        awcc.CPUFanIdx = 1
        awcc.Mode.Custom = 0
        awcc.Mode.Balanced = 1
        awcc.Mode.Performance = 2
        awcc.Mode.Quiet = 3
        awcc.Mode.G_Mode = 4
        awcc.setMode.return_value = True
        awcc.getFanRPM.return_value = 2500

        with patch('GUI.AppGUI.DetectHardware') as mock_dh:
            mock_dh_inst = mock_dh.return_value
            mock_dh_inst.getHardwareName.return_value = 'Test Device'

            window = TCC_GUI(awcc)
            window._toasterMessageCurrentMode = MagicMock()
            window.toasterMessage = MagicMock()

            # Set starting mode to Balanced
            window._modeSwitch.setChecked(ThermalMode.Balanced.value)
            assert window._modeSwitch.getChecked() == ThermalMode.Balanced.value

            # Turn user soft fail-safe OFF
            window._failsafeOn = False

            # Phase A: Soft high temp excursion (96°C CPU, limit is 95°C)
            # awcc returns 96°C for CPU, 65°C for GPU
            awcc.getFanRelatedTemp.side_effect = lambda idx: 65 if idx == awcc.GPUFanIdx else 96
            window._gpuTemp.read = MagicMock(return_value=65)

            # First tick initializes start timestamp
            window._updateAppState()
            # Backdate soft start timestamp past 8-second delay
            window._failsafeTempIsHighStartTs = time.time() - 10.0

            # Second tick: soft trip would trigger IF _failsafeOn was True, but it is False
            window._updateAppState()
            assert window._modeSwitch.getChecked() == ThermalMode.Balanced.value, (
                "Soft fail-safe must respect user disable toggle"
            )

            # Phase B: Hard critical excursion (101°C CPU, hard limit is 100°C)
            awcc.getFanRelatedTemp.side_effect = lambda idx: 65 if idx == awcc.GPUFanIdx else 101
            window._updateAppState()

            # Backdate hard start timestamp past 4-second delay
            window._failsafeHardTempStartTs = time.time() - (window.FAILSAFE_HARD_TRIGGER_DELAY_SEC + 1.0)

            # Next tick: MUST trip to G_Mode despite _failsafeOn=False
            window._updateAppState()
            assert window._modeSwitch.getChecked() == ThermalMode.G_Mode.value, (
                "INV-1 VIOLATION: Hard fail-safe must trip to G_Mode even when _failsafeOn is False!"
            )
            assert window._failsafeTrippedPrevModeStr == ThermalMode.Balanced.value
    finally:
        HotKey.start = orig_hotkey
        TCC_GUI._startWatchdog = orig_watchdog

