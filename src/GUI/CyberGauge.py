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
        self.setFixedHeight(18)
        self.setMinimumWidth(55)

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
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.3px;
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
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.3px;
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
            # Fan RPM Tachometer: Neon Green -> Cyber Yellow -> Crimson
            span = max(1, self._max - self._min)
            ratio = (self._val - self._min) / span
            if ratio >= 0.82:
                return QtGui.QColor("#FF003C")
            elif ratio >= 0.60:
                return QtGui.QColor("#FCEE0A")
            return QtGui.QColor("#00FF66")

    def paintEvent(self, event: QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        # 25-degree skewed parallelogram geometry (tan(25°) ≈ 0.4663)
        skew = round(h * 0.4663, 1)

        # 1. Background Track (25° Angled Parallelogram) - Translucent Dark Carbon
        track_path = QtGui.QPainterPath()
        track_path.moveTo(skew + 1.0, 1.5)
        track_path.lineTo(w - 2.0, 1.5)
        track_path.lineTo(w - 2.0 - skew, h - 1.5)
        track_path.lineTo(1.0, h - 1.5)
        track_path.closeSubpath()

        # Dark translucent carbon surface over acrylic glass
        painter.fillPath(track_path, QtGui.QColor(15, 20, 30, 190))

        # Cyber border with neon cyan glow
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 240, 255, 90), 1.0))
        painter.drawPath(track_path)

        # 2. Fill calculation
        span = self._max - self._min
        if span <= 0: span = 1
        pct = max(0.0, min(1.0, (self._val - self._min) / span))

        usable_w = w - skew - 5.0
        fill_w = usable_w * pct

        if fill_w > 1.5:
            fill_path = QtGui.QPainterPath()
            fill_path.moveTo(skew + 1.5, 3.0)
            fill_path.lineTo(skew + 1.5 + fill_w, 3.0)
            fill_path.lineTo(1.5 + fill_w, h - 3.0)
            fill_path.lineTo(1.5, h - 3.0)
            fill_path.closeSubpath()

            # Sharp Cyberpunk Neon Gradient (#00FF66 -> #FCEE0A -> #FF003C)
            grad = QtGui.QLinearGradient(skew + 1.5, 0.0, skew + 1.5 + usable_w, 0.0)
            if self._color_limits:
                p0 = max(0.0, min(1.0, (self._color_limits[0] - self._min) / span))
                p1 = max(p0, min(1.0, (self._color_limits[1] - self._min) / span))
                grad.setColorAt(0.0, QtGui.QColor("#00FF66"))
                grad.setColorAt(max(0.0, p0 - 0.04), QtGui.QColor("#00FF66"))
                grad.setColorAt(p0, QtGui.QColor("#FCEE0A"))
                grad.setColorAt(max(p0, p1 - 0.04), QtGui.QColor("#FCEE0A"))
                grad.setColorAt(p1, QtGui.QColor("#FF003C"))
                grad.setColorAt(1.0, QtGui.QColor("#FF003C"))
            else:
                grad.setColorAt(0.0, QtGui.QColor("#00FF66"))
                grad.setColorAt(0.60, QtGui.QColor("#FCEE0A"))
                grad.setColorAt(0.85, QtGui.QColor("#FF003C"))
                grad.setColorAt(1.0, QtGui.QColor("#FF003C"))

            painter.fillPath(fill_path, QtGui.QBrush(grad))

            # Specular top glow line
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 220), 1.0))
            painter.drawLine(QtCore.QPointF(skew + 1.5, 3.0), QtCore.QPointF(skew + 1.5 + fill_w, 3.0))

        # 3. Tactical Divider Hatches along the gauge (diagonal tech hatches)
        num_segments = 8
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 160), 1.2))
        for i in range(1, num_segments):
            frac = i / float(num_segments)
            x_top = skew + 1.5 + usable_w * frac
            x_bot = 1.5 + usable_w * frac
            painter.drawLine(QtCore.QPointF(x_top, 2.5), QtCore.QPointF(x_bot, h - 2.5))

        # 4. Tactical Tick Marks on bottom
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 240, 255, 110), 1.0))
        for step in [0.0, 0.50, 1.0]:
            x_b = 1.5 + usable_w * step
            painter.drawLine(QtCore.QPointF(x_b, h - 1.5), QtCore.QPointF(x_b - 1.5, h + 1.0))

        painter.end()
