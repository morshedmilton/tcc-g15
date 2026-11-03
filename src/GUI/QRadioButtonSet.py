from typing import Callable, Optional, Tuple, Union
from PySide6 import QtCore, QtWidgets

class QRadioButtonSet(QtWidgets.QWidget):
    _buttons: dict[str, QtWidgets.QRadioButton]
    _userCallback: Optional[Callable[[str], None]]

    def __init__(self, parent: Optional[QtWidgets.QWidget], title: Optional[str],
                 options: list[Tuple[str, str]],
                 layout: Optional[Union[QtWidgets.QHBoxLayout, QtWidgets.QVBoxLayout]] = None) -> None:
        super().__init__(parent)
        if len(options) == 0:
            raise RuntimeError('"options" list length can not be 0')

        self.setObjectName('SegmentedControl')

        if layout is None:
            layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        self.setLayout(layout)

        if title:
            lbl = QtWidgets.QLabel(title)
            lbl.setStyleSheet("color: #8b92a0; font-size: 11px; font-weight: 500; margin-right: 4px;")
            layout.addWidget(lbl)

        self._userCallback = None
        self._buttons = {}
        for label, value in options:
            rb = QtWidgets.QRadioButton(label)
            rb._value = value
            rb.setFixedHeight(26)
            rb.setCursor(QtCore.Qt.PointingHandCursor)
            layout.addWidget(rb)
            self._buttons[value] = rb
            rb.setChecked(True)
            rb.toggled.connect(self._onClicked)

        # Style as Apple/Linear segmented liquid glass pill
        self.setStyleSheet("""
            QWidget#SegmentedControl {
                background: rgba(0, 0, 0, 0.40);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
            QRadioButton {
                color: #8e95a5;
                font-size: 11px;
                font-weight: 500;
                padding: 4px 10px;
                border-radius: 6px;
                border: 1px solid transparent;
                background: transparent;
            }
            QRadioButton::indicator {
                width: 0px;
                height: 0px;
            }
            QRadioButton:hover {
                color: #f5f5f7;
                background: rgba(255, 255, 255, 0.06);
            }
            QRadioButton:checked {
                color: #ffffff;
                font-weight: 600;
                background: rgba(255, 255, 255, 0.14);
                border: 1px solid rgba(255, 255, 255, 0.20);
            }
            QRadioButton:disabled {
                color: #4a5060;
                background: transparent;
            }
        """)

    def setChecked(self, value: str):
        button = self._buttons.get(value)
        if button is not None and not button.isChecked():
            button.setChecked(True)

    def getChecked(self) -> Optional[str]:
        for rb in self._buttons.values():
            if rb.isChecked():
                return rb._value
        return None

    def setOnChange(self, callback: Callable[[str], None]) -> None:
        self._userCallback = callback

    def setOptionEnabled(self, value: str, enabled: bool) -> None:
        if value in self._buttons:
            self._buttons[value].setEnabled(enabled)

    @QtCore.Slot()
    def _onClicked(self):
        rb = self.sender() # type: QtWidgets.QRadioButton
        if self._userCallback and rb.isChecked():
            self._userCallback(rb._value)
