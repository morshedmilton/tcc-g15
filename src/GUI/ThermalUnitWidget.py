from typing import Callable, Optional, Tuple
from PySide6 import QtCore, QtWidgets, QtGui
from GUI.QGauge import QGauge
from GUI.AppColors import Colors

class ThermalUnitWidget(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget], tempMinMax: Tuple[int,int], tempColorLimits: Optional[Tuple[int,int]], fanMinMax: Tuple[int,int], sliderMaxAndTick: Tuple[int,int]):
        super().__init__(parent)
        self.setObjectName("ThermalCard")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        # Header: Hardware Title + Category Tag Pill
        self._title = QtWidgets.QLabel(self)
        self._title.setStyleSheet("color: #f5f5f7; font-size: 13px; font-weight: 600; letter-spacing: -0.2px;")
        
        self._tagPill = QtWidgets.QLabel(self)
        self._tagPill.setStyleSheet("""
            background: rgba(10, 132, 255, 0.14);
            color: #5ac8fa;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 8px;
            border: 1px solid rgba(90, 200, 250, 0.20);
        """)

        headerLayout = QtWidgets.QHBoxLayout()
        headerLayout.setContentsMargins(0, 0, 0, 2)
        headerLayout.addWidget(self._title, alignment=QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        headerLayout.addStretch(1)
        headerLayout.addWidget(self._tagPill, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Temp Row: [TEMP] [======Bar======] [ 52 °C ]
        lblTemp = QtWidgets.QLabel("TEMP")
        lblTemp.setFixedWidth(42)
        lblTemp.setStyleSheet("color: #6b7280; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")

        self._tempBar, self._tempBarLabel = self._makeGaugeWithLabel(tempMinMax, ' °C', tempColorLimits)
        self._tempBarLabel.setFixedWidth(56)

        tempLayout = QtWidgets.QHBoxLayout()
        tempLayout.setSpacing(8)
        tempLayout.addWidget(lblTemp, alignment=QtCore.Qt.AlignVCenter)
        tempLayout.addWidget(self._tempBar, 1, alignment=QtCore.Qt.AlignVCenter)
        tempLayout.addWidget(self._tempBarLabel, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Fan Row: [FAN] [======Bar======] [ 2400 RPM ]
        lblFan = QtWidgets.QLabel("FAN")
        lblFan.setFixedWidth(42)
        lblFan.setStyleSheet("color: #6b7280; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")

        self._fanBar, self._fanBarLabel = self._makeGaugeWithLabel(fanMinMax, ' RPM')
        self._fanBarLabel.setFixedWidth(72)

        fanLayout = QtWidgets.QHBoxLayout()
        fanLayout.setSpacing(8)
        fanLayout.addWidget(lblFan, alignment=QtCore.Qt.AlignVCenter)
        fanLayout.addWidget(self._fanBar, 1, alignment=QtCore.Qt.AlignVCenter)
        fanLayout.addWidget(self._fanBarLabel, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Custom Fan Speed Offset Slider Row
        lblOffset = QtWidgets.QLabel("OFFSET")
        lblOffset.setFixedWidth(42)
        lblOffset.setStyleSheet("color: #6b7280; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")

        self._speedSliderCallback = None
        self._speedSlider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        self._speedSlider.setMaximum(sliderMaxAndTick[0])
        self._speedSlider.setTickInterval(sliderMaxAndTick[1])
        self._speedSlider.setTickPosition(QtWidgets.QSlider.NoTicks)
        self._speedSlider.setFixedHeight(16)
        self._speedSlider.setToolTip(
            "Fan speed offset over the BIOS curve.\n"
            "Active in Custom mode. Firmware floor is ~3000 RPM.")
        self._speedSliderDebounce = QtCore.QTimer()
        self._speedSliderDebounce.setInterval(500)
        self._speedSliderDebounce.setSingleShot(True)
        self._speedSliderDebounce.timeout.connect(self._onSpeedSliderChange)
        self._speedSlider.valueChanged.connect(self._onSliderMoved)

        self._sliderValLabel = QtWidgets.QLabel("+0%")
        self._sliderValLabel.setFixedWidth(40)
        self._sliderValLabel.setStyleSheet("color: #8e95a5; font-size: 11px; font-weight: 600;")
        self._sliderValLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        sliderLayout = QtWidgets.QHBoxLayout()
        sliderLayout.setSpacing(8)
        sliderLayout.addWidget(lblOffset, alignment=QtCore.Qt.AlignVCenter)
        sliderLayout.addWidget(self._speedSlider, 1, alignment=QtCore.Qt.AlignVCenter)
        sliderLayout.addWidget(self._sliderValLabel, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Main Card Layout
        cardLayout = QtWidgets.QVBoxLayout(self)
        cardLayout.setContentsMargins(14, 12, 14, 12)
        cardLayout.setSpacing(7)
        cardLayout.addLayout(headerLayout)
        cardLayout.addLayout(tempLayout)
        cardLayout.addLayout(fanLayout)
        cardLayout.addLayout(sliderLayout)

    def _makeGaugeWithLabel(self, minMax: Tuple[int,int], units: str, colorLimits: Optional[Tuple[int,int]] = None) -> Tuple[QGauge, QtWidgets.QLabel]:
        g = QGauge()
        g.setMinimum(minMax[0])
        g.setMaximum(minMax[1])
        if colorLimits:
            g.setColorScheme({colorLimits[0]: Colors.GREEN.value, colorLimits[1]: Colors.YELLOW.value, minMax[1]: Colors.RED.value})
        g.setFormat(f'%v{units}')
        return (g, g.createLabel())

    def _onSliderMoved(self, val: int):
        self._sliderValLabel.setText(f"+{val}%")
        self._speedSliderDebounce.start()

    def setTitle(self, title: str) -> None:
        self._title.setText(title)
        # Update category pill automatically
        upper = title.upper()
        if "GPU" in upper or "RTX" in upper or "GEFORCE" in upper or "GRAPHICS" in upper:
            self._tagPill.setText("GPU")
            self._tagPill.setStyleSheet("""
                background: rgba(10, 132, 255, 0.14);
                color: #5ac8fa;
                font-size: 10px;
                font-weight: 700;
                padding: 2px 7px;
                border-radius: 8px;
                border: 1px solid rgba(90, 200, 250, 0.20);
            """)
        elif "CPU" in upper or "CORE" in upper or "INTEL" in upper or "RYZEN" in upper:
            self._tagPill.setText("CPU")
            self._tagPill.setStyleSheet("""
                background: rgba(48, 209, 88, 0.14);
                color: #30d158;
                font-size: 10px;
                font-weight: 700;
                padding: 2px 7px;
                border-radius: 8px;
                border: 1px solid rgba(48, 209, 88, 0.20);
            """)
        else:
            self._tagPill.setText("UNIT")

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
        self._sliderValLabel.setStyleSheet(
            "color: #4a5060; font-size: 11px; font-weight: 600;" if disabled
            else "color: #5ac8fa; font-size: 11px; font-weight: 600;"
        )

    def getSpeedSlider(self) -> int:
        return self._speedSlider.value()

    def setSpeedSlider(self, speed: int) -> None:
        self._speedSlider.setValue(speed)
        self._sliderValLabel.setText(f"+{speed}%")

    def _onSpeedSliderChange(self) -> None:
        if self._speedSliderCallback:
            self._speedSliderCallback()
