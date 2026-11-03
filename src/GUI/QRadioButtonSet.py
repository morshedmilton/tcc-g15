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

        self.setObjectName('CyberModeSelector')
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        hLayout = QtWidgets.QHBoxLayout(self)
        hLayout.setContentsMargins(0, 0, 0, 0)
        hLayout.setSpacing(6)

        if title:
            lbl = QtWidgets.QLabel(title)
            lbl.setStyleSheet("color: #7D8799; font-family: 'Orbitron', monospace; font-size: 11px; font-weight: bold; margin-right: 4px;")
            hLayout.addWidget(lbl)

        self._buttonGroup = QtWidgets.QButtonGroup(self)
        self._buttonGroup.setExclusive(True)

        self._userCallback = None
        self._buttons = {}
        for label, value in options:
            btnText = label.upper().replace('_', ' ')
            if "G MODE" in btnText or "G_MODE" in btnText:
                btnText = "G-MODE // OVRD"
            btn = QtWidgets.QPushButton(btnText)
            btn._value = value
            btn.setCheckable(True)
            btn.setFixedHeight(30)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            if "G_MODE" in value or "G-MODE" in btnText:
                btn.setProperty("isGMode", True)
            self._buttonGroup.addButton(btn)
            hLayout.addWidget(btn)
            self._buttons[value] = btn
            btn.toggled.connect(self._onClicked)

        # High-tech Cyberpunk Mode Selector Stylesheet
        self.setStyleSheet("""
            QWidget#CyberModeSelector {
                background: transparent;
            }
            QPushButton {
                background: rgba(20, 26, 38, 0.70);
                color: #8A96AA;
                font-family: 'Orbitron', 'Cascadia Code', monospace;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 0.6px;
                padding: 4px 12px;
                border: 1px solid rgba(0, 240, 255, 0.20);
                border-radius: 2px;
            }
            QPushButton:hover {
                background: rgba(0, 240, 255, 0.18);
                color: #00F0FF;
                border: 1px solid #00F0FF;
            }
            QPushButton:checked {
                background: #FCEE0A;
                color: #05070A;
                font-weight: 900;
                border: 1px solid #FFFFFF;
                border-radius: 2px;
            }
            QPushButton[isGMode="true"]:checked {
                background: #FF003C;
                color: #FFFFFF;
                border: 1px solid #FFAAB8;
            }
            QPushButton:disabled {
                color: #4A5262;
                background: rgba(15, 18, 25, 0.40);
                border-color: rgba(255, 255, 255, 0.05);
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
