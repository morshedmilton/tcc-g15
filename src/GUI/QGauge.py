from typing import Optional
from PySide6 import QtCore, QtWidgets

class QGauge(QtWidgets.QProgressBar):
    _colorScheme: Optional[dict[int, str]]
    _extLabel: Optional[QtWidgets.QLabel]

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName('QGauge')
        self._updColor_connected = False
        self._colorScheme = None
        self._extLabel = None
        self.setTextVisible(False)
        self.setFixedHeight(6)

    def setColorScheme(self, colorScheme: dict[int, str]) -> None:
        self._colorScheme = colorScheme
        self._updateColor()

    def createLabel(self) -> QtWidgets.QLabel:
        if not self._extLabel:
            self._extLabel = QtWidgets.QLabel()
            self._extLabel.setStyleSheet("""
                color: #f5f5f7;
                font-size: 13px;
                font-weight: 600;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
            """)
            self._extLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        return self._extLabel

    def setValue(self, value: int):
        if self._extLabel:
            self._extLabel.setText(self.format().replace('%v', str(value)))
        if value < self.minimum(): value = self.minimum()
        if value > self.maximum(): value = self.maximum()
        super().setValue(value)
        self._updateColor()

    def _updateColor(self):
        if self._colorScheme:
            val = self.value()
            gradStop0 = '#30d158'
            gradStop1 = '#34c759'
            textColor = '#30d158'
            
            # Find matching limit
            for lim, c in self._colorScheme.items():
                if c == '#ffd60a': # Yellow
                    if val >= lim:
                        gradStop0 = '#ffd60a'
                        gradStop1 = '#ff9f0a'
                        textColor = '#ffd60a'
                elif c == '#ff453a': # Red
                    if val >= lim:
                        gradStop0 = '#ff453a'
                        gradStop1 = '#ff3b30'
                        textColor = '#ff453a'

            if self._extLabel:
                self._extLabel.setStyleSheet(f"""
                    color: {textColor};
                    font-size: 13px;
                    font-weight: 700;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
                """)

            self.setStyleSheet(f"""
                QGauge {{
                    background: rgba(255, 255, 255, 0.08);
                    border: none;
                    border-radius: 3px;
                    max-height: 6px;
                    min-height: 6px;
                }}
                QGauge::chunk {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {gradStop0}, stop:1 {gradStop1});
                    border-radius: 3px;
                }}
            """)
        else:
            self.setStyleSheet("""
                QGauge {
                    background: rgba(255, 255, 255, 0.08);
                    border: none;
                    border-radius: 3px;
                    max-height: 6px;
                    min-height: 6px;
                }
                QGauge::chunk {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0a84ff, stop:1 #5ac8fa);
                    border-radius: 3px;
                }
            """)
