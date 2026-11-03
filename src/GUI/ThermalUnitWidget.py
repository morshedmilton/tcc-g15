from typing import Callable, Optional, Tuple
from PySide6 import QtCore, QtWidgets
from GUI.QGauge import QGauge
from GUI.AppColors import Colors

class ThermalUnitWidget(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget], tempMinMax: Tuple[int,int], tempColorLimits: Optional[Tuple[int,int]], fanMinMax: Tuple[int,int], sliderMaxAndTick: Tuple[int,int]):
        super().__init__(parent)
        self.setObjectName("ThermalCard")

        self._title = QtWidgets.QLabel(self)
        self._title.setStyleSheet("color: #f5f5f7; font-size: 13px; font-weight: 600;")
        self._title.hide()

        self._subTitle = QtWidgets.QLabel(self)
        self._subTitle.setStyleSheet("color: #a1a7b5; font-size: 11px; font-weight: 500;")
        self._subTitle.hide()
        self._subTitle.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self._subTitle.setToolTip("Triple left-click and Ctrl+C to copy")

        self._tempBar, _tempBarLabel = self._makeGaugeWithLabel(tempMinMax, ' °C', tempColorLimits)
        self._fanBar, _fanBarLabel = self._makeGaugeWithLabel(fanMinMax, ' RPM')

        self._speedSliderCallback = None
        self._speedSlider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        self._speedSlider.setMaximum(sliderMaxAndTick[0])
        self._speedSlider.setTickInterval(sliderMaxAndTick[1])
        self._speedSlider.setTickPosition(QtWidgets.QSlider.NoTicks)
        self._speedSlider.setFixedHeight(18)
        self._speedSlider.setToolTip(
            "Fan speed offset over the BIOS curve.\n"
            "Active in Custom mode. Firmware floor is ~3000 RPM.")
        self._speedSliderDebounce = QtCore.QTimer()
        self._speedSliderDebounce.setInterval(500)
        self._speedSliderDebounce.setSingleShot(True)
        self._speedSliderDebounce.timeout.connect(self._onSpeedSliderChange)
        self._speedSlider.valueChanged.connect(lambda: self._speedSliderDebounce.start())
        
        # Linear/Apple layout: Clean card with header, metrics, and sleek slider
        grid = QtWidgets.QGridLayout()
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setVerticalSpacing(6)
        grid.setHorizontalSpacing(10)

        # Header
        grid.addWidget(self._title,         0, 0, 1, 2, QtCore.Qt.AlignLeft)
        grid.addWidget(self._subTitle,      0, 0, 1, 2, QtCore.Qt.AlignLeft)

        # Temp gauge and readout
        grid.addWidget(self._tempBar,       1, 0, QtCore.Qt.AlignVCenter)
        grid.addWidget(_tempBarLabel,       1, 1, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Fan gauge and readout
        grid.addWidget(self._fanBar,        2, 0, QtCore.Qt.AlignVCenter)
        grid.addWidget(_fanBarLabel,        2, 1, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Slider spanning across bottom (no redundant "Fan Speed" secondary label)
        grid.addWidget(self._speedSlider,   3, 0, 1, 2, QtCore.Qt.AlignVCenter)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)
        self.setLayout(grid)

    def _makeGaugeWithLabel(self, minMax: Tuple[int,int], units: str, colorLimits: Optional[Tuple[int,int]] = None) -> Tuple[QGauge, QtWidgets.QLabel]:
        g = QGauge()
        g.setMinimum(minMax[0])
        g.setMaximum(minMax[1])
        if colorLimits:
            g.setColorScheme({colorLimits[0]: Colors.GREEN.value, colorLimits[1]: Colors.YELLOW.value, minMax[1]: Colors.RED.value})
        g.setFormat(f'%v{units}')
        return (g, g.createLabel())
    
    def setTitle(self, title: str) -> None:
        if len(title) < 14:
            self._title.setText(title)
            self._subTitle.hide()
            self._title.show()
        else:
            self._subTitle.setText(title)
            self._title.hide()
            self._subTitle.show()

    def setTemp(self, temp: int) -> None:
        self._tempBar.setValue(temp)

    def getTemp(self) -> int:
        return self._tempBar.value()

    def setFanRPM(self, rpm: int) -> None:
        self._fanBar.setValue(rpm)

    def setSourceNote(self, note: str) -> None:
        self._tempBar.setToolTip(note)

    def speedSliderChanged(self, callback: Callable) -> None:
        self._speedSliderCallback = callback

    def setSpeedDisabled(self, disabled: bool) -> None:
        self._speedSlider.setDisabled(disabled)

    def getSpeedSlider(self) -> int:
        return self._speedSlider.value()

    def setSpeedSlider(self, value: Optional[int] = None) -> None:
        if value is None: value = (self._speedSlider.minimum() + self._speedSlider.maximum()) // 2
        if value < self._speedSlider.minimum(): value = self._speedSlider.minimum()
        if value > self._speedSlider.maximum(): value = self._speedSlider.maximum()
        self._speedSlider.setValue(value)

    @QtCore.Slot()
    def _onSpeedSliderChange(self) -> None:
        if self._speedSliderCallback:
            self._speedSliderCallback()
