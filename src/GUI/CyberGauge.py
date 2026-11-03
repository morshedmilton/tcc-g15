from typing import Optional, Tuple, Dict, Any
from PySide6 import QtCore, QtGui, QtWidgets

class CyberGauge(QtWidgets.QWidget):
    """
    High-Tech Cyberpunk HUD Skewed Segmented Gauge.
    Inspired by Cyberpunk 2077, military avionics, and futuristic racing telemetry.
    Features:
    - Skewed 25-degree angled track with chamfered geometry
    - Futuristic diagonal hatch ticks and gradient fill
    - Dynamic color shift: Cool Cyan (#00F0FF) -> Cyber Warning Yellow (#FCEE0A) -> Hazard Red (#FF003C)
    - High-performance vector QPainter rendering with zero CPU wakeups
    """
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, min_val: int = 0, max_val: int = 100, unit: str = ""):
        super().__init__(parent)
        self.setObjectName("CyberGauge")
        self._min = min_val
        self._max = max_val
        self._val = min_val
        self._unit = unit
        self._color_limits: Optional[Tuple[int, int]] = None
        self._extLabel: Optional[QtWidgets.QLabel] = None
        self.setFixedHeight(22)
        self.setMinimumWidth(180)

    def setMinimum(self, val: int):
        self._min = val
        self.update()

    def setMaximum(self, val: int):
        self._max = val
        self.update()

    def value(self) -> int:
        return self._val

    def minimum(self) -> int:
        return self._min

    def maximum(self) -> int:
        return self._max

    def setColorLimits(self, limits: Tuple[int, int]):
        self._color_limits = limits
        self.update()

    def setColorScheme(self, scheme: Dict[int, Any]):
        # Translate {lim0: color1, lim1: color2, ...}
        keys = sorted(scheme.keys())
        if len(keys) >= 2:
            self._color_limits = (keys[0], keys[1])
        elif len(keys) == 1:
            self._color_limits = (keys[0], keys[0] + 10)
        self.update()

    def setFormat(self, fmt: str):
        self._unit = fmt.replace('%v', '')

    def format(self) -> str:
        return f"%v{self._unit}"

    def createLabel(self) -> QtWidgets.QLabel:
        if not self._extLabel:
            self._extLabel = QtWidgets.QLabel(f"{self._val}{self._unit}")
            color = self._getCurrentColor()
            self._extLabel.setStyleSheet(f"""
                color: {color.name()};
                font-family: 'Orbitron', 'Cascadia Code', 'Consolas', monospace;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 0.5px;
            """)
            self._extLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        return self._extLabel

    def setValue(self, val: int):
        val = max(self._min, min(self._max, val))
        self._val = val
        color = self._getCurrentColor()
        if self._extLabel:
            self._extLabel.setText(f"{val}{self._unit}")
            self._extLabel.setStyleSheet(f"""
                color: {color.name()};
                font-family: 'Orbitron', 'Cascadia Code', 'Consolas', monospace;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 0.5px;
            """)
        self.update()

    def _getCurrentColor(self) -> QtGui.QColor:
        if self._color_limits:
            if self._val >= self._color_limits[1]:
                return QtGui.QColor("#FF003C") # Critical Overheat / Hazard Red
            elif self._val >= self._color_limits[0]:
                return QtGui.QColor("#FCEE0A") # Cyber Warning Yellow
            return QtGui.QColor("#00FF66") # Optimal Green
        else:
            # Fan RPM Tachometer: Cyan -> Cyber Yellow -> Crimson
            span = max(1, self._max - self._min)
            ratio = (self._val - self._min) / span
            if ratio > 0.82:
                return QtGui.QColor("#FF003C")
            elif ratio > 0.60:
                return QtGui.QColor("#FCEE0A")
            return QtGui.QColor("#00F0FF")

    def paintEvent(self, event: QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        skew = 10.0 # Skew offset in pixels (approx 25 degrees)

        # 1. Background Track (Angled Parallelogram)
        track_path = QtGui.QPainterPath()
        track_path.moveTo(skew, 2.0)
        track_path.lineTo(w - 2.0, 2.0)
        track_path.lineTo(w - 2.0 - skew, h - 2.0)
        track_path.lineTo(2.0, h - 2.0)
        track_path.closeSubpath()

        # Dark translucent carbon surface
        painter.fillPath(track_path, QtGui.QColor(15, 20, 30, 210))

        # Cyber border with neon cyan glow
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 240, 255, 80), 1.0))
        painter.drawPath(track_path)

        # 2. Fill calculation
        span = self._max - self._min
        if span <= 0: span = 1
        pct = max(0.0, min(1.0, (self._val - self._min) / span))

        usable_w = w - skew - 6.0
        fill_w = usable_w * pct

        if fill_w > 1.5:
            color = self._getCurrentColor()
            fill_path = QtGui.QPainterPath()
            fill_path.moveTo(skew + 2.0, 4.0)
            fill_path.lineTo(skew + 2.0 + fill_w, 4.0)
            fill_path.lineTo(2.0 + fill_w, h - 4.0)
            fill_path.lineTo(4.0, h - 4.0)
            fill_path.closeSubpath()

            # Glowing gradient fill
            grad = QtGui.QLinearGradient(0.0, 0.0, w, 0.0)
            grad.setColorAt(0.0, color.lighter(130))
            grad.setColorAt(1.0, color)
            painter.fillPath(fill_path, QtGui.QBrush(grad))

            # Specular top glow line
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 220), 1.2))
            painter.drawLine(QtCore.QPointF(skew + 2.0, 4.0), QtCore.QPointF(skew + 2.0 + fill_w, 4.0))

        # 3. Tactical Divider Hatches along the gauge
        num_segments = 12
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 160), 1.5))
        for i in range(1, num_segments):
            frac = i / float(num_segments)
            x_top = skew + 2.0 + usable_w * frac
            x_bot = 2.0 + usable_w * frac
            painter.drawLine(QtCore.QPointF(x_top, 3.0), QtCore.QPointF(x_bot, h - 3.0))

        # 4. Tactical Tick Marks on bottom
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 240, 255, 120), 1.0))
        for step in [0.0, 0.25, 0.50, 0.75, 1.0]:
            x_b = 2.0 + usable_w * step
            painter.drawLine(QtCore.QPointF(x_b, h - 2.0), QtCore.QPointF(x_b - 2.0, h + 1.0))

        painter.end()
