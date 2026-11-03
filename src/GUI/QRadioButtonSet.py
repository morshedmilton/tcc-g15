from typing import Callable, Optional, Tuple, Union
from PySide6 import QtCore, QtWidgets

class QRadioButtonSet(QtWidgets.QWidget):
    _buttons: dict[str, QtWidgets.QPushButton]
    _userCallback: Optional[Callable[[str], None]]

    def __init__(self, parent: Optional[QtWidgets.QWidget], title: Optional[str],
                 options: list[Tuple[str, str]],
                 layout: Optional[Union[QtWidgets.QHBoxLayout, QtWidgets.QVBoxLayout]] = None) -> None:
        super().__init__(parent)
        if len(options) == 0:
            raise RuntimeError('"options" list length can not be 0')

        self.setObjectName('GlassSegmentedControl')
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        hLayout = QtWidgets.QHBoxLayout(self)
        hLayout.setContentsMargins(4, 4, 4, 4)
        hLayout.setSpacing(4)

        if title:
            lbl = QtWidgets.QLabel(title)
            lbl.setStyleSheet("color: #8b92a0; font-size: 11px; font-weight: 500; margin-right: 4px;")
            hLayout.addWidget(lbl)

        self._buttonGroup = QtWidgets.QButtonGroup(self)
        self._buttonGroup.setExclusive(True)

        self._userCallback = None
        self._buttons = {}
        for label, value in options:
            btn = QtWidgets.QPushButton(label)
            btn._value = value
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            self._buttonGroup.addButton(btn)
            hLayout.addWidget(btn)
            self._buttons[value] = btn
            btn.toggled.connect(self._onClicked)

        # Style as true Apple Liquid Glass segmented control
        self.setStyleSheet("""
            QWidget#GlassSegmentedControl {
                background: rgba(0, 0, 0, 0.25);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
            }
            QPushButton {
                color: #8e95a5;
                font-size: 12px;
                font-weight: 500;
                padding: 4px 12px;
                border-radius: 10px;
                border: 1px solid transparent;
                background: transparent;
            }
            QPushButton:hover {
                color: #f5f5f7;
                background: rgba(255, 255, 255, 0.06);
            }
            QPushButton:checked {
                color: #ffffff;
                font-weight: 600;
                background: rgba(255, 255, 255, 0.16);
                border: 1px solid rgba(255, 255, 255, 0.24);
            }
            QPushButton:disabled {
                color: #4a5060;
                background: transparent;
            }
        """)

    def setChecked(self, value: str):
        btn = self._buttons.get(value)
        if btn is not None and not btn.isChecked():
            btn.setChecked(True)

    def getChecked(self) -> Optional[str]:
        for btn in self._buttons.values():
            if btn.isChecked():
                return btn._value
        return None

    def setOnChange(self, callback: Callable[[str], None]) -> None:
        self._userCallback = callback

    def setOptionEnabled(self, value: str, enabled: bool) -> None:
        if value in self._buttons:
            self._buttons[value].setEnabled(enabled)

    @QtCore.Slot(bool)
    def _onClicked(self, checked: bool):
        btn = self.sender()
        if self._userCallback and checked and btn:
            self._userCallback(btn._value)
