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

        # A default argument here used to be a single shared QHBoxLayout instance, so every
        # QRadioButtonSet in the process reparented its buttons into the same layout.
        if layout is None:
            layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.setLayout(layout)

        if title:
            layout.addWidget(QtWidgets.QLabel(title))

        self._userCallback = None
        self._buttons = {}
        for label, value in options:
            rb = QtWidgets.QRadioButton(label)
            rb._value = value
            rb.setMinimumHeight(22)
            rb.setCursor(QtCore.Qt.PointingHandCursor)
            layout.addWidget(rb)
            self._buttons[value] = rb
            rb.setChecked(True)
            rb.toggled.connect(self._onClicked)

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
