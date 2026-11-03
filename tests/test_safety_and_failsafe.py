import pytest
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
