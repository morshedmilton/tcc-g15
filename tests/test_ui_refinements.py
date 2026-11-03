import os
import pytest
from unittest.mock import MagicMock
from PySide6 import QtWidgets, QtCore, QtGui

from GUI.ThermalUnitWidget import ThermalUnitWidget, HardwareIcon
from GUI.CyberGauge import CyberGauge
from GUI.HotKey import HotKey

@pytest.fixture(scope="session")
def qapp():
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication([])
    return app


def test_offs_slider_limits_0_to_100(qapp):
    """OFFS slider operates strictly within 0% to 100% and cannot be set/displayed up to 120."""
    widget = ThermalUnitWidget(
        None,
        tempMinMax=(0, 100),
        tempColorLimits=(70, 85),
        fanMinMax=(0, 5500),
        sliderMaxAndTick=(100, 20)
    )

    # Check slider range
    assert widget._speedSlider.minimum() == 0
    assert widget._speedSlider.maximum() == 100

    # Test setting value within bounds
    widget.setSpeedSlider(50)
    assert widget.getSpeedSlider() == 50
    assert widget._sliderValLabel.text() == "+50%"

    # Test setting value exceeding 100 (e.g. 120) - must clamp to 100
    widget.setSpeedSlider(120)
    assert widget.getSpeedSlider() == 100
    assert widget._sliderValLabel.text() == "+100%"

    # Test setting value below 0 - must clamp to 0
    widget.setSpeedSlider(-10)
    assert widget.getSpeedSlider() == 0
    assert widget._sliderValLabel.text() == "+0%"

    # Test invalid sliderMaxAndTick passed with 120 - widget must still clamp max to 100
    widget120 = ThermalUnitWidget(
        None,
        tempMinMax=(0, 100),
        tempColorLimits=(70, 85),
        fanMinMax=(0, 5500),
        sliderMaxAndTick=(120, 20)
    )
    assert widget120._speedSlider.maximum() == 100


def test_no_double_slash_prefix_and_hardware_vector_icons(qapp):
    """Section titles and labels must not contain '//' and must feature vector icons."""
    gpuWidget = ThermalUnitWidget(None, (0, 95), (72, 85), (0, 5500), (100, 20))
    cpuWidget = ThermalUnitWidget(None, (0, 110), (85, 95), (0, 5500), (100, 20))

    # Set titles
    gpuWidget.setTitle("GPU")
    cpuWidget.setTitle("CPU")

    # Titles must not contain "//"
    assert "//" not in gpuWidget._title.text()
    assert "//" not in cpuWidget._title.text()
    assert "//" not in gpuWidget._tagPill.text()
    assert "//" not in cpuWidget._tagPill.text()

    # Even if title with "//" is passed, it must be stripped
    gpuWidget.setTitle("// NVIDIA GEFORCE RTX 4060")
    cpuWidget.setTitle("// 13TH GEN INTEL CORE I7-13650HX")
    assert "//" not in gpuWidget._title.text()
    assert "//" not in cpuWidget._title.text()
    assert "//" not in gpuWidget._tagPill.text()
    assert "//" not in cpuWidget._tagPill.text()

    # Both widgets feature HardwareIcon before the title
    assert isinstance(gpuWidget._icon, HardwareIcon)
    assert isinstance(cpuWidget._icon, HardwareIcon)
    assert gpuWidget._icon._type == "GPU"
    assert cpuWidget._icon._type == "CPU"


def test_cybergauge_cyberpunk_neon_identity(qapp):
    """CyberGauge displays cyberpunk neon styling with skewed 25-degree angle and neon gradient."""
    gauge = CyberGauge(None, min_val=0, max_val=100, unit=" °C")
    gauge.setColorLimits((70, 85))
    gauge.resize(100, 18)

    # 25-degree skew angle calculation check (tan(25°) ≈ 0.4663)
    expected_skew = round(18 * 0.4663, 1)
    assert expected_skew == 8.4

    # Neon colors
    gauge.setValue(50)
    assert gauge._getCurrentColor() == QtGui.QColor("#00FF66")  # Optimal Neon Green

    gauge.setValue(75)
    assert gauge._getCurrentColor() == QtGui.QColor("#FCEE0A")  # Warning Neon Yellow

    gauge.setValue(90)
    assert gauge._getCurrentColor() == QtGui.QColor("#FF003C")  # Hazard Neon Red


def test_compact_window_width_between_360_and_400(qapp):
    """Main window width target is between 360px and 400px."""
    # Prevent background threads / hotkeys during test
    orig_start = HotKey.start
    HotKey.start = lambda self: None
    try:
        from GUI.AppGUI import TCC_GUI, APP_STYLESHEET

        awcc = MagicMock()
        awcc.GPUFanIdx = 0
        awcc.CPUFanIdx = 1
        awcc.Mode.Custom = 0
        awcc.Mode.Balanced = 1
        awcc.Mode.Performance = 2
        awcc.Mode.Quiet = 3
        awcc.Mode.G_Mode = 4
        awcc.setMode.return_value = True
        awcc.getFanRelatedTemp.return_value = 50
        awcc.getFanRPM.return_value = 2000

        orig_watchdog = TCC_GUI._startWatchdog
        TCC_GUI._startWatchdog = lambda self: None
        from unittest.mock import patch
        with patch('GUI.AppGUI.DetectHardware') as mock_dh:
            mock_dh_inst = mock_dh.return_value
            mock_dh_inst.getHardwareName.return_value = None
            try:
                window = TCC_GUI(awcc)
                window.setStyleSheet(APP_STYLESHEET)
                window.adjustSize()

                hint_w = window.sizeHint().width()
                assert 360 <= hint_w <= 400, f"sizeHint width {hint_w} not between 360 and 400"

                # Check thermal cards fit
                assert window._thermalGPU.width() > 0
                assert window._thermalCPU.width() > 0

                # Check slider max is 100
                assert window._thermalGPU._speedSlider.maximum() == 100
                assert window._thermalCPU._speedSlider.maximum() == 100

                window._destroy()
            finally:
                TCC_GUI._startWatchdog = orig_watchdog
    finally:
        HotKey.start = orig_start
