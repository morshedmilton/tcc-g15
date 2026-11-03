from typing import Callable, Optional, Tuple
from PySide6 import QtCore, QtWidgets, QtGui
from GUI.CyberGauge import CyberGauge

class HardwareIcon(QtWidgets.QWidget):
    """Clean Cyberpunk Hardware Vector Icon for CPU and GPU."""
    def __init__(self, hardware_type: str = 'CPU', parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._type = hardware_type.upper()
        self.setFixedSize(14, 14)

    def setType(self, hardware_type: str):
        self._type = hardware_type.upper()
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        w = float(self.width())
        h = float(self.height())

        if "GPU" in self._type:
            # Clean GPU Vector Icon: graphics board with PCIe edge, heatsink, and dual cooler fans
            color = QtGui.QColor("#00F0FF")
            pen = QtGui.QPen(color, 1.2)
            painter.setPen(pen)
            # Main board outline
            painter.drawRoundedRect(QtCore.QRectF(1.0, 2.0, w - 2.0, h - 4.5), 1.0, 1.0)
            # PCIe connector pins on bottom
            painter.drawLine(QtCore.QPointF(3.0, h - 2.5), QtCore.QPointF(w - 3.0, h - 2.5))
            painter.drawLine(QtCore.QPointF(4.0, h - 1.5), QtCore.QPointF(7.0, h - 1.5))
            # Dual cooler fan circles
            painter.setPen(QtGui.QPen(color, 1.0))
            painter.drawEllipse(QtCore.QPointF(w * 0.35, h * 0.45), 2.0, 2.0)
            painter.drawEllipse(QtCore.QPointF(w * 0.68, h * 0.45), 2.0, 2.0)
        else:
            # Clean CPU Vector Icon: square chip package with center core die and contact pins
            color = QtGui.QColor("#00FF66")
            pen = QtGui.QPen(color, 1.2)
            painter.setPen(pen)
            # Outer chip package
            painter.drawRoundedRect(QtCore.QRectF(2.5, 2.5, w - 5.0, h - 5.0), 1.0, 1.0)
            # Center core die
            painter.fillRect(QtCore.QRectF(4.8, 4.8, w - 9.6, h - 9.6), QtGui.QBrush(color))
            # Contact pins (top, bottom, left, right)
            painter.setPen(QtGui.QPen(color, 1.0))
            # Top pins
            painter.drawLine(QtCore.QPointF(4.5, 0.8), QtCore.QPointF(4.5, 2.2))
            painter.drawLine(QtCore.QPointF(w - 4.5, 0.8), QtCore.QPointF(w - 4.5, 2.2))
            # Bottom pins
            painter.drawLine(QtCore.QPointF(4.5, h - 2.2), QtCore.QPointF(4.5, h - 0.8))
            painter.drawLine(QtCore.QPointF(w - 4.5, h - 2.2), QtCore.QPointF(w - 4.5, h - 0.8))
            # Left pins
            painter.drawLine(QtCore.QPointF(0.8, 4.5), QtCore.QPointF(2.2, 4.5))
            painter.drawLine(QtCore.QPointF(0.8, h - 4.5), QtCore.QPointF(2.2, h - 4.5))
            # Right pins
            painter.drawLine(QtCore.QPointF(w - 2.2, 4.5), QtCore.QPointF(w - 0.8, 4.5))
            painter.drawLine(QtCore.QPointF(w - 2.2, h - 4.5), QtCore.QPointF(w - 0.8, h - 4.5))

        painter.end()


class ThermalUnitWidget(QtWidgets.QFrame):
    def __init__(self, parent: Optional[QtWidgets.QWidget], tempMinMax: Tuple[int,int], tempColorLimits: Optional[Tuple[int,int]], fanMinMax: Tuple[int,int], sliderMaxAndTick: Tuple[int,int], hardwareType: Optional[str] = None):
        super().__init__(parent)
        self.setObjectName("CyberCard")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self._hardwareType: Optional[str] = hardwareType.upper() if hardwareType else None

        # Header: Hardware Vector Icon + Title + Status Tag
        self._icon = HardwareIcon(self._hardwareType or "CPU", self)

        self._title = QtWidgets.QLabel(self)
        self._title.setStyleSheet("color: #FFFFFF; font-family: 'Orbitron', 'Cascadia Code', monospace; font-size: 11px; font-weight: 800; letter-spacing: 0.3px;")

        self._tagPill = QtWidgets.QLabel("LIVE", self)
        self._tagPill.setStyleSheet("""
            color: #00F0FF;
            font-family: 'Orbitron', 'Cascadia Code', monospace;
            font-size: 9px;
            font-weight: bold;
            background: rgba(0, 240, 255, 0.12);
            padding: 1px 4px;
            border: 1px solid rgba(0, 240, 255, 0.35);
            border-radius: 2px;
        """)

        headerLayout = QtWidgets.QHBoxLayout()
        headerLayout.setContentsMargins(0, 0, 0, 1)
        headerLayout.setSpacing(4)
        headerLayout.addWidget(self._icon, alignment=QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        headerLayout.addWidget(self._title, alignment=QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        headerLayout.addStretch(1)
        headerLayout.addWidget(self._tagPill, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Temp Row: [TEMP] [===CyberGauge===] [ 62 °C ]
        lblTemp = QtWidgets.QLabel("TEMP")
        lblTemp.setFixedWidth(30)
        lblTemp.setStyleSheet("color: #00F0FF; font-family: 'Orbitron', 'Cascadia Code', monospace; font-size: 9px; font-weight: bold;")

        self._tempBar = CyberGauge(self, min_val=tempMinMax[0], max_val=tempMinMax[1], unit=' °C')
        if tempColorLimits:
            self._tempBar.setColorLimits(tempColorLimits)
        self._tempBarLabel = self._tempBar.createLabel()
        self._tempBarLabel.setFixedWidth(42)

        tempLayout = QtWidgets.QHBoxLayout()
        tempLayout.setSpacing(4)
        tempLayout.addWidget(lblTemp, alignment=QtCore.Qt.AlignVCenter)
        tempLayout.addWidget(self._tempBar, 1, alignment=QtCore.Qt.AlignVCenter)
        tempLayout.addWidget(self._tempBarLabel, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Fan Row: [TACH] [===CyberGauge===] [ 2700 RPM ]
        lblFan = QtWidgets.QLabel("TACH")
        lblFan.setFixedWidth(30)
        lblFan.setStyleSheet("color: #00F0FF; font-family: 'Orbitron', 'Cascadia Code', monospace; font-size: 9px; font-weight: bold;")

        self._fanBar = CyberGauge(self, min_val=fanMinMax[0], max_val=fanMinMax[1], unit=' RPM')
        self._fanBarLabel = self._fanBar.createLabel()
        self._fanBarLabel.setFixedWidth(54)

        fanLayout = QtWidgets.QHBoxLayout()
        fanLayout.setSpacing(4)
        fanLayout.addWidget(lblFan, alignment=QtCore.Qt.AlignVCenter)
        fanLayout.addWidget(self._fanBar, 1, alignment=QtCore.Qt.AlignVCenter)
        fanLayout.addWidget(self._fanBarLabel, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Custom Fan Speed Offset Slider Row: [OFFS] [===Slider===] [ +0% ]
        self._lblOffset = QtWidgets.QLabel("OFFS")
        self._lblOffset.setFixedWidth(30)
        self._lblOffset.setStyleSheet("color: #7D8799; font-family: 'Orbitron', 'Cascadia Code', monospace; font-size: 9px; font-weight: bold;")

        self._speedSliderCallback = None
        self._speedSlider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        # Constrain strictly to 0-100% scale (fixing the previous 120 limit)
        maxVal = min(100, sliderMaxAndTick[0]) if sliderMaxAndTick and sliderMaxAndTick[0] > 0 else 100
        tickVal = sliderMaxAndTick[1] if sliderMaxAndTick else 20
        self._speedSlider.setRange(0, maxVal)
        self._speedSlider.setTickInterval(tickVal)
        self._speedSlider.setTickPosition(QtWidgets.QSlider.NoTicks)
        self._speedSlider.setFixedHeight(14)
        self._speedSlider.setToolTip(
            "Fan speed offset over the BIOS curve.\n"
            "Active in Custom mode. Firmware floor is ~3000 RPM.")
        self._speedSliderDebounce = QtCore.QTimer()
        self._speedSliderDebounce.setInterval(500)
        self._speedSliderDebounce.setSingleShot(True)
        self._speedSliderDebounce.timeout.connect(self._onSpeedSliderChange)
        self._speedSlider.valueChanged.connect(self._onSliderMoved)

        self._sliderValLabel = QtWidgets.QLabel("+0%")
        self._sliderValLabel.setFixedWidth(36)
        self._sliderValLabel.setStyleSheet("color: #FCEE0A; font-family: 'Orbitron', monospace; font-size: 10px; font-weight: bold;")
        self._sliderValLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        sliderLayout = QtWidgets.QHBoxLayout()
        sliderLayout.setSpacing(4)
        sliderLayout.addWidget(self._lblOffset, alignment=QtCore.Qt.AlignVCenter)
        sliderLayout.addWidget(self._speedSlider, 1, alignment=QtCore.Qt.AlignVCenter)
        sliderLayout.addWidget(self._sliderValLabel, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Main Card Layout
        cardLayout = QtWidgets.QVBoxLayout(self)
        cardLayout.setContentsMargins(6, 6, 6, 6)
        cardLayout.setSpacing(4)
        cardLayout.addLayout(headerLayout)
        cardLayout.addLayout(tempLayout)
        cardLayout.addLayout(fanLayout)
        cardLayout.addLayout(sliderLayout)

    def _onSliderMoved(self, val: int):
        val = max(0, min(100, int(val)))
        self._sliderValLabel.setText(f"+{val}%")
        self._speedSliderDebounce.start()

    def setTitle(self, title: Optional[str]) -> None:
        clean_title = (title or "").replace("//", "").strip()
        upper = clean_title.upper()

        if self._hardwareType == "GPU":
            is_gpu = True
            is_cpu = False
        elif self._hardwareType == "CPU":
            is_gpu = False
            is_cpu = True
        else:
            import re
            is_cpu = (
                "CPU" in upper
                or "CORE" in upper
                or "RYZEN" in upper
                or bool(re.search(r'i[3579]-\w+', upper))
            )
            is_gpu = not is_cpu and (
                "GPU" in upper
                or "RTX" in upper
                or "GTX" in upper
                or "GEFORCE" in upper
                or "GRAPHICS" in upper
                or "RADEON" in upper
                or "ARC" in upper
            )

        if is_gpu:
            self._hardwareType = "GPU"
            self._icon.setType("GPU")
            self._tagPill.setText("LIVE")
            self._tagPill.setStyleSheet("""
                color: #00F0FF;
                font-family: 'Orbitron', 'Cascadia Code', monospace;
                font-size: 9px;
                font-weight: bold;
                background: rgba(0, 240, 255, 0.12);
                padding: 1px 4px;
                border: 1px solid rgba(0, 240, 255, 0.35);
                border-radius: 2px;
            """)
            if "RTX" in upper:
                idx = upper.find("RTX")
                parts = clean_title[idx:].split()
                if len(parts) >= 3 and parts[2].upper() == "TI":
                    display_title = f"{parts[0]} {parts[1]} TI".upper()
                else:
                    display_title = (" ".join(parts[:2]) if len(parts) >= 2 else "GPU").upper()
            elif "GTX" in upper:
                idx = upper.find("GTX")
                parts = clean_title[idx:].split()
                if len(parts) >= 3 and parts[2].upper() == "TI":
                    display_title = f"{parts[0]} {parts[1]} TI".upper()
                else:
                    display_title = (" ".join(parts[:2]) if len(parts) >= 2 else "GPU").upper()
            elif "RX" in upper:
                idx = upper.find("RX")
                parts = clean_title[idx:].split()
                if len(parts) >= 3 and parts[2].upper() in ("XT", "XTX"):
                    display_title = f"{parts[0]} {parts[1]} {parts[2]}".upper()
                else:
                    display_title = (" ".join(parts[:2]) if len(parts) >= 2 else "GPU").upper()
            elif "RADEON" in upper:
                display_title = "RADEON"
            elif "ARC" in upper:
                idx = upper.find("ARC")
                parts = clean_title[idx:].split()
                if len(parts) >= 2 and parts[1].upper().startswith("A"):
                    display_title = f"ARC {parts[1]}".upper()
                else:
                    display_title = "ARC GPU"
            else:
                display_title = "GPU"
        elif is_cpu:
            self._hardwareType = "CPU"
            self._icon.setType("CPU")
            self._tagPill.setText("LIVE")
            self._tagPill.setStyleSheet("""
                color: #00FF66;
                font-family: 'Orbitron', 'Cascadia Code', monospace;
                font-size: 9px;
                font-weight: bold;
                background: rgba(0, 255, 102, 0.12);
                padding: 1px 4px;
                border: 1px solid rgba(0, 255, 102, 0.35);
                border-radius: 2px;
            """)
            import re
            m = re.search(r'(i[3579][-\s]\w+|Ultra\s*\d+\s*\w*|Ryzen\s*(?:AI\s*)?[3579]\s*(?:HX\s*)?\w+)', clean_title, re.IGNORECASE)
            if m:
                raw = m.group(1)
                if re.match(r'Ryzen\s*(?:AI\s*)?([3579])\s*(?:HX\s*)?(\w+)', raw, re.IGNORECASE):
                    rm = re.match(r'Ryzen\s*(?:AI\s*)?([3579])\s*(?:HX\s*)?(\w+)', raw, re.IGNORECASE)
                    display_title = f"R{rm.group(1)} {rm.group(2)}".upper()
                elif re.match(r'Ultra\s*([3579])\s*(\w+)', raw, re.IGNORECASE):
                    um = re.match(r'Ultra\s*([3579])\s*(\w+)', raw, re.IGNORECASE)
                    display_title = f"U{um.group(1)} {um.group(2)}".upper()
                elif re.match(r'i([3579])[-\s](\w+)', raw, re.IGNORECASE):
                    im = re.match(r'i([3579])[-\s](\w+)', raw, re.IGNORECASE)
                    display_title = f"I{im.group(1)}-{im.group(2)}".upper()
                else:
                    display_title = raw.upper()
            else:
                display_title = "CPU"
        else:
            self._icon.setType("CPU")
            self._tagPill.setText("READY")
            self._tagPill.setStyleSheet("""
                color: #7D8799;
                font-family: 'Orbitron', 'Cascadia Code', monospace;
                font-size: 9px;
                font-weight: bold;
                background: rgba(255, 255, 255, 0.08);
                padding: 1px 4px;
                border: 1px solid rgba(255, 255, 255, 0.20);
                border-radius: 2px;
            """)
            display_title = clean_title[:8].upper() if clean_title else "UNIT"

        if len(display_title) > 11:
            display_title = display_title[:11]
        self._title.setText(display_title)
        if clean_title and clean_title not in ("CPU", "GPU"):
            self._title.setToolTip(clean_title)

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
            self._lblOffset.setStyleSheet("color: #4A5262; font-family: 'Orbitron', 'Cascadia Code', monospace; font-size: 9px; font-weight: bold;")
            self._sliderValLabel.setStyleSheet("color: #4A5262; font-family: 'Orbitron', monospace; font-size: 10px; font-weight: bold;")
        else:
            self._lblOffset.setStyleSheet("color: #00F0FF; font-family: 'Orbitron', 'Cascadia Code', monospace; font-size: 9px; font-weight: bold;")
            self._sliderValLabel.setStyleSheet("color: #FCEE0A; font-family: 'Orbitron', monospace; font-size: 10px; font-weight: bold;")

    def getSpeedSlider(self) -> int:
        return max(0, min(100, int(self._speedSlider.value())))

    def setSpeedSlider(self, speed: int) -> None:
        try:
            val = max(0, min(100, int(speed))) if speed is not None else 0
        except (ValueError, TypeError):
            val = 0
        self._speedSlider.setValue(val)
        self._sliderValLabel.setText(f"+{val}%")

    def _onSpeedSliderChange(self) -> None:
        if self._speedSliderCallback:
            self._speedSliderCallback()
