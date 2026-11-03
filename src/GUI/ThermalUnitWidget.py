from typing import Callable, Optional, Tuple
from PySide6 import QtCore, QtWidgets, QtGui
from GUI.CyberGauge import CyberGauge

class ThermalUnitWidget(QtWidgets.QFrame):
    def __init__(self, parent: Optional[QtWidgets.QWidget], tempMinMax: Tuple[int,int], tempColorLimits: Optional[Tuple[int,int]], fanMinMax: Tuple[int,int], sliderMaxAndTick: Tuple[int,int]):
        super().__init__(parent)
        self.setObjectName("CyberCard")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        # Header: Hardware Title + Status Tag
        self._title = QtWidgets.QLabel(self)
        self._title.setStyleSheet("color: #FFFFFF; font-family: 'Orbitron', 'Cascadia Code', monospace; font-size: 13px; font-weight: 800; letter-spacing: 0.5px;")

        self._tagPill = QtWidgets.QLabel(self)
        self._tagPill.setStyleSheet("""
            color: #00F0FF;
            font-family: 'Orbitron', 'Cascadia Code', monospace;
            font-size: 10px;
            font-weight: bold;
            background: rgba(0, 240, 255, 0.12);
            padding: 2px 7px;
            border: 1px solid rgba(0, 240, 255, 0.35);
            border-radius: 2px;
        """)

        headerLayout = QtWidgets.QHBoxLayout()
        headerLayout.setContentsMargins(0, 0, 0, 2)
        headerLayout.addWidget(self._title, alignment=QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        headerLayout.addStretch(1)
        headerLayout.addWidget(self._tagPill, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Temp Row: [:: TEMP] [===CyberGauge===] [ 62 °C ]
        lblTemp = QtWidgets.QLabel(":: TEMP")
        lblTemp.setFixedWidth(55)
        lblTemp.setStyleSheet("color: #00F0FF; font-family: 'Orbitron', 'Cascadia Code', monospace; font-size: 11px; font-weight: bold;")

        self._tempBar = CyberGauge(self, min_val=tempMinMax[0], max_val=tempMinMax[1], unit=' °C')
        if tempColorLimits:
            self._tempBar.setColorLimits(tempColorLimits)
        self._tempBarLabel = self._tempBar.createLabel()
        self._tempBarLabel.setFixedWidth(64)

        tempLayout = QtWidgets.QHBoxLayout()
        tempLayout.setSpacing(8)
        tempLayout.addWidget(lblTemp, alignment=QtCore.Qt.AlignVCenter)
        tempLayout.addWidget(self._tempBar, 1, alignment=QtCore.Qt.AlignVCenter)
        tempLayout.addWidget(self._tempBarLabel, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Fan Row: [:: TACH] [===CyberGauge===] [ 2700 RPM ]
        lblFan = QtWidgets.QLabel(":: TACH")
        lblFan.setFixedWidth(55)
        lblFan.setStyleSheet("color: #00F0FF; font-family: 'Orbitron', 'Cascadia Code', monospace; font-size: 11px; font-weight: bold;")

        self._fanBar = CyberGauge(self, min_val=fanMinMax[0], max_val=fanMinMax[1], unit=' RPM')
        self._fanBarLabel = self._fanBar.createLabel()
        self._fanBarLabel.setFixedWidth(82)

        fanLayout = QtWidgets.QHBoxLayout()
        fanLayout.setSpacing(8)
        fanLayout.addWidget(lblFan, alignment=QtCore.Qt.AlignVCenter)
        fanLayout.addWidget(self._fanBar, 1, alignment=QtCore.Qt.AlignVCenter)
        fanLayout.addWidget(self._fanBarLabel, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Custom Fan Speed Offset Slider Row: [:: OFFS] [===Slider===] [ +0% ]
        self._lblOffset = QtWidgets.QLabel(":: OFFS")
        self._lblOffset.setFixedWidth(55)
        self._lblOffset.setStyleSheet("color: #7D8799; font-family: 'Orbitron', 'Cascadia Code', monospace; font-size: 11px; font-weight: bold;")

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
        self._sliderValLabel.setFixedWidth(52)
        self._sliderValLabel.setStyleSheet("color: #FCEE0A; font-family: 'Orbitron', monospace; font-size: 11px; font-weight: bold;")
        self._sliderValLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        sliderLayout = QtWidgets.QHBoxLayout()
        sliderLayout.setSpacing(8)
        sliderLayout.addWidget(self._lblOffset, alignment=QtCore.Qt.AlignVCenter)
        sliderLayout.addWidget(self._speedSlider, 1, alignment=QtCore.Qt.AlignVCenter)
        sliderLayout.addWidget(self._sliderValLabel, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Main Card Layout
        cardLayout = QtWidgets.QVBoxLayout(self)
        cardLayout.setContentsMargins(14, 12, 14, 12)
        cardLayout.setSpacing(8)
        cardLayout.addLayout(headerLayout)
        cardLayout.addLayout(tempLayout)
        cardLayout.addLayout(fanLayout)
        cardLayout.addLayout(sliderLayout)

    def _onSliderMoved(self, val: int):
        self._sliderValLabel.setText(f"+{val}%")
        self._speedSliderDebounce.start()

    def setTitle(self, title: str) -> None:
        self._title.setText(f"// {title.upper()}")
        upper = title.upper()
        if "GPU" in upper or "RTX" in upper or "GEFORCE" in upper or "GRAPHICS" in upper:
            self._tagPill.setText("[ GPU // ACTIVE ]")
            self._tagPill.setStyleSheet("""
                color: #00F0FF;
                font-family: 'Orbitron', 'Cascadia Code', monospace;
                font-size: 10px;
                font-weight: bold;
                background: rgba(0, 240, 255, 0.12);
                padding: 2px 7px;
                border: 1px solid rgba(0, 240, 255, 0.35);
                border-radius: 2px;
            """)
        elif "CPU" in upper or "CORE" in upper or "INTEL" in upper or "RYZEN" in upper:
            self._tagPill.setText("[ CPU // ACTIVE ]")
            self._tagPill.setStyleSheet("""
                color: #00FF66;
                font-family: 'Orbitron', 'Cascadia Code', monospace;
                font-size: 10px;
                font-weight: bold;
                background: rgba(0, 255, 102, 0.12);
                padding: 2px 7px;
                border: 1px solid rgba(0, 255, 102, 0.35);
                border-radius: 2px;
            """)
        else:
            self._tagPill.setText("[ UNIT // READY ]")

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
        if disabled:
            self._lblOffset.setStyleSheet("color: #4A5262; font-family: 'Orbitron', 'Cascadia Code', monospace; font-size: 11px; font-weight: bold;")
            self._sliderValLabel.setStyleSheet("color: #4A5262; font-family: 'Orbitron', monospace; font-size: 11px; font-weight: bold;")
        else:
            self._lblOffset.setStyleSheet("color: #00F0FF; font-family: 'Orbitron', 'Cascadia Code', monospace; font-size: 11px; font-weight: bold;")
            self._sliderValLabel.setStyleSheet("color: #FCEE0A; font-family: 'Orbitron', monospace; font-size: 11px; font-weight: bold;")

    def getSpeedSlider(self) -> int:
        return self._speedSlider.value()

    def setSpeedSlider(self, speed: int) -> None:
        self._speedSlider.setValue(speed)
        self._sliderValLabel.setText(f"+{speed}%")

    def _onSpeedSliderChange(self) -> None:
        if self._speedSliderCallback:
            self._speedSliderCallback()
