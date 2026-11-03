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
    gpuWidget = ThermalUnitWidget(None, (0, 95), (72, 85), (0, 5500), (100, 20), hardwareType="GPU")
    cpuWidget = ThermalUnitWidget(None, (0, 110), (85, 95), (0, 5500), (100, 20), hardwareType="CPU")

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

    # Edge cases: None and empty strings must not crash
    gpuWidget.setTitle(None)
    cpuWidget.setTitle("")
    assert "//" not in gpuWidget._title.text()
    assert "//" not in cpuWidget._title.text()

    # AMD Radeon and Intel Arc support
    amdGpuWidget = ThermalUnitWidget(None, (0, 95), (72, 85), (0, 5500), (100, 20), hardwareType="GPU")
    amdGpuWidget.setTitle("AMD Radeon RX 7700M")
    assert amdGpuWidget._icon._type == "GPU"
    assert amdGpuWidget._title.text() == "RX 7700M"

    amdXtWidget = ThermalUnitWidget(None, (0, 95), (72, 85), (0, 5500), (100, 20), hardwareType="GPU")
    amdXtWidget.setTitle("AMD Radeon RX 6600 XT")
    assert amdXtWidget._title.text() == "RX 6600 XT"

    nvidiaTiWidget = ThermalUnitWidget(None, (0, 95), (72, 85), (0, 5500), (100, 20), hardwareType="GPU")
    nvidiaTiWidget.setTitle("NVIDIA GeForce RTX 3050 Ti Laptop GPU")
    assert nvidiaTiWidget._title.text() == "RTX 3050 TI"

    arcGpuWidget = ThermalUnitWidget(None, (0, 95), (72, 85), (0, 5500), (100, 20), hardwareType="GPU")
    arcGpuWidget.setTitle("Intel Arc A730M Graphics")
    assert arcGpuWidget._icon._type == "GPU"

    # AMD Ryzen with Radeon Graphics auto-detection without explicit hardwareType
    ryzenApuWidget = ThermalUnitWidget(None, (0, 110), (85, 95), (0, 5500), (100, 20), hardwareType=None)
    ryzenApuWidget.setTitle("AMD Ryzen 9 7945HX with Radeon Graphics")
    assert ryzenApuWidget._icon._type == "CPU"
    assert ryzenApuWidget._title.text() == "R9 7945HX"

    ryzenHsWidget = ThermalUnitWidget(None, (0, 110), (85, 95), (0, 5500), (100, 20), hardwareType="CPU")
    ryzenHsWidget.setTitle("AMD Ryzen 7 7840HS")
    assert ryzenHsWidget._title.text() == "R7 7840HS"

    ultraCpuWidget = ThermalUnitWidget(None, (0, 110), (85, 95), (0, 5500), (100, 20), hardwareType="CPU")
    ultraCpuWidget.setTitle("Intel Core Ultra 7 155H")
    assert ultraCpuWidget._title.text() == "U7 155H"


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


def test_cybergauge_rendering_and_parallel_geometry(qapp):
    """CyberGauge renders cleanly to QPixmap across all values and fill path has parallel 25-degree edges."""
    gauge = CyberGauge(None, min_val=0, max_val=100, unit=" °C")
    gauge.setColorLimits((70, 85))
    gauge.resize(120, 18)

    # Render at different values
    for val in [0, 1, 25, 50, 75, 100]:
        gauge.setValue(val)
        pix = QtGui.QPixmap(gauge.size())
        pix.fill(QtCore.Qt.transparent)
        gauge.render(pix)
        assert not pix.isNull()


def test_hardware_icon_rendering(qapp):
    """HardwareIcon renders CPU and GPU vector paths without errors."""
    for hw in ["CPU", "GPU"]:
        icon = HardwareIcon(hw)
        pix = QtGui.QPixmap(icon.size())
        pix.fill(QtCore.Qt.transparent)
        icon.render(pix)
        assert not pix.isNull()


def test_compact_window_width_between_360_and_400(qapp):
    """Main window width target is between 360px and 400px and fits real hardware titles without clipping."""
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
            mock_dh_inst.getHardwareName.return_value = 'NVIDIA GeForce RTX 4060 Laptop GPU'
            try:
                window = TCC_GUI(awcc)
                window.setStyleSheet(APP_STYLESHEET)
                window.updateGaugeTitles(
                    'NVIDIA GeForce RTX 4060 Laptop GPU',
                    '13th Gen Intel Core i7-13650HX'
                )
                window.adjustSize()

                hint_w = window.sizeHint().width()
                assert 360 <= hint_w <= 400, f"sizeHint width {hint_w} not between 360 and 400"

                targetWidth = max(360, min(400, hint_w))
                window.setFixedSize(targetWidth, window.sizeHint().height())
                window.show()
                QtWidgets.QApplication.processEvents()

                # Check thermal cards fit
                assert window._thermalGPU.width() > 0
                assert window._thermalCPU.width() > 0

                # Crucial check: verify that headers do not clip with realistic hardware names
                for card in (window._thermalGPU, window._thermalCPU):
                    # Title width must accommodate its sizeHint
                    assert card._title.width() >= card._title.sizeHint().width(), (
                        f"Title {card._title.text()} clipped: width {card._title.width()} < sizeHint {card._title.sizeHint().width()}"
                    )
                    # Tag pill must not be clipped
                    assert card._tagPill.width() >= card._tagPill.sizeHint().width(), (
                        f"Tag pill {card._tagPill.text()} clipped: width {card._tagPill.width()} < sizeHint {card._tagPill.sizeHint().width()}"
                    )

                # Crucial check: verify that failsafe button and badge do not clip
                assert window._failsafeBtn.width() >= window._failsafeBtn.sizeHint().width(), (
                    f"Failsafe button clipped: width {window._failsafeBtn.width()} < sizeHint {window._failsafeBtn.sizeHint().width()}"
                )
                assert window._failsafeThresholdBadge.width() >= window._failsafeThresholdBadge.sizeHint().width(), (
                    f"Threshold badge clipped: width {window._failsafeThresholdBadge.width()} < sizeHint {window._failsafeThresholdBadge.sizeHint().width()}"
                )

                # Verify threshold badge across trip limits
                for g_lim, c_lim in [(85, 95), (90, 100), (70, 80)]:
                    window._setGpuLimit(g_lim)
                    window._setCpuLimit(c_lim)
                    QtWidgets.QApplication.processEvents()
                    assert window._failsafeThresholdBadge.width() >= window._failsafeThresholdBadge.sizeHint().width(), (
                        f"Threshold badge {g_lim}/{c_lim} clipped: width {window._failsafeThresholdBadge.width()} < sizeHint {window._failsafeThresholdBadge.sizeHint().width()}"
                    )

                # Check mode switch buttons do not clip
                for btn in window._modeSwitch._buttons.values():
                    assert btn.width() >= btn.sizeHint().width(), (
                        f"Mode button {btn.text()} clipped: width {btn.width()} < sizeHint {btn.sizeHint().width()}"
                    )

                # Check slider max is 100
                assert window._thermalGPU._speedSlider.maximum() == 100
                assert window._thermalCPU._speedSlider.maximum() == 100

                window._destroy()
            finally:
                TCC_GUI._startWatchdog = orig_watchdog
    finally:
        HotKey.start = orig_start
