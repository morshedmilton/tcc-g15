"""ProcessRulesDialog: Configuration UI for process-aware automatic profile switching.

Implements REQ-0605 with master toggle, rules table, rule editor dialog,
QSettings persistence under 'process_rules' and 'auto_switch_enabled', and preset reset.
"""
from __future__ import annotations

import json
from typing import List, Optional
from PySide6 import QtCore, QtWidgets

from Backend.ProcessRule import ProcessRule
from Backend.ProcessRulePresets import get_default_presets

# Must match the profiles the window offers (MODE_ORDER). Listing a profile that is
# silently coerced made the dialog promise something it did not do (DEF-711).
SUPPORTED_MODES = ["Auto", "Balanced", "G_Mode", "Custom"]

DIALOG_STYLESHEET = """
QDialog {
    background-color: #0E121C;
    color: #E2E8F0;
    border: 1px solid rgba(0, 240, 255, 0.40);
    border-radius: 6px;
    font-family: 'Orbitron', 'Cascadia Code', 'Segoe UI', sans-serif;
}
QTableWidget {
    background-color: rgba(18, 24, 38, 0.75);
    border: 1px solid rgba(0, 240, 255, 0.25);
    border-radius: 4px;
    gridline-color: rgba(0, 240, 255, 0.15);
    color: #FFFFFF;
    selection-background-color: rgba(0, 240, 255, 0.30);
    selection-color: #FCEE0A;
}
QHeaderView::section {
    background-color: #161D2E;
    color: #00F0FF;
    border: 1px solid rgba(0, 240, 255, 0.20);
    padding: 4px;
    font-weight: bold;
    font-size: 10px;
}
QPushButton {
    background: rgba(20, 28, 44, 0.80);
    color: #00F0FF;
    border: 1px solid rgba(0, 240, 255, 0.35);
    border-radius: 3px;
    padding: 5px 12px;
    font-size: 10px;
    font-weight: bold;
}
QPushButton:hover {
    background: rgba(0, 240, 255, 0.20);
    border: 1px solid #00F0FF;
    color: #FFFFFF;
}
QPushButton#ResetBtn {
    color: #FCEE0A;
    border-color: rgba(252, 238, 10, 0.40);
}
QPushButton#ResetBtn:hover {
    background: rgba(252, 238, 10, 0.20);
    border-color: #FCEE0A;
    color: #FFFFFF;
}
QPushButton#RemoveBtn {
    color: #FF003C;
    border-color: rgba(255, 0, 60, 0.40);
}
QPushButton#RemoveBtn:hover {
    background: rgba(255, 0, 60, 0.20);
    border-color: #FF003C;
    color: #FFFFFF;
}
QCheckBox {
    color: #FFFFFF;
    font-size: 11px;
    font-weight: bold;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #00F0FF;
    border-radius: 2px;
    background: rgba(14, 18, 28, 0.8);
}
QCheckBox::indicator:checked {
    background: #00FF66;
}
QLineEdit, QComboBox {
    background: rgba(18, 24, 38, 0.90);
    border: 1px solid rgba(0, 240, 255, 0.35);
    color: #FFFFFF;
    padding: 4px;
    border-radius: 2px;
    font-size: 11px;
}
QLabel {
    color: #FFFFFF;
    font-size: 11px;
}
"""


class RuleEditDialog(QtWidgets.QDialog):
    """Sub-dialog for adding or modifying an individual process rule."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, rule: Optional[ProcessRule] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Rule" if rule else "Add Rule")
        self.setFixedSize(360, 200)
        self.setStyleSheet(DIALOG_STYLESHEET)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Process Executable
        row1 = QtWidgets.QHBoxLayout()
        lbl1 = QtWidgets.QLabel("Executable:")
        lbl1.setFixedWidth(85)
        self.txtExecutable = QtWidgets.QLineEdit()
        self.txtExecutable.setPlaceholderText("e.g. cs2.exe")
        if rule:
            self.txtExecutable.setText(rule.process_name)
        row1.addWidget(lbl1)
        row1.addWidget(self.txtExecutable)
        layout.addLayout(row1)

        # Target Thermal Mode
        row2 = QtWidgets.QHBoxLayout()
        lbl2 = QtWidgets.QLabel("Target Mode:")
        lbl2.setFixedWidth(85)
        self.comboMode = QtWidgets.QComboBox()
        self.comboMode.addItems(SUPPORTED_MODES)
        if rule and rule.target_mode in SUPPORTED_MODES:
            self.comboMode.setCurrentText(rule.target_mode)
        elif rule and rule.target_mode == "G Mode":
            self.comboMode.setCurrentText("G_Mode")
        row2.addWidget(lbl2)
        row2.addWidget(self.comboMode)
        layout.addLayout(row2)

        # Description
        row3 = QtWidgets.QHBoxLayout()
        lbl3 = QtWidgets.QLabel("Description:")
        lbl3.setFixedWidth(85)
        self.txtDescription = QtWidgets.QLineEdit()
        self.txtDescription.setPlaceholderText("e.g. Counter-Strike 2")
        if rule:
            self.txtDescription.setText(rule.description)
        row3.addWidget(lbl3)
        row3.addWidget(self.txtDescription)
        layout.addLayout(row3)

        # Enabled Checkbox
        self.chkEnabled = QtWidgets.QCheckBox("Rule Active")
        self.chkEnabled.setChecked(rule.enabled if rule else True)
        layout.addWidget(self.chkEnabled)

        # Buttons
        btnLayout = QtWidgets.QHBoxLayout()
        btnLayout.addStretch(1)
        btnSave = QtWidgets.QPushButton("Save")
        btnSave.clicked.connect(self._on_save)
        btnCancel = QtWidgets.QPushButton("Cancel")
        btnCancel.clicked.connect(self.reject)
        btnLayout.addWidget(btnSave)
        btnLayout.addWidget(btnCancel)
        layout.addLayout(btnLayout)

        self._rule_result: Optional[ProcessRule] = None

    def _on_save(self) -> None:
        exe = ProcessRule.normalize_process_name(self.txtExecutable.text())
        if not exe:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Executable name cannot be empty.")
            return

        self._rule_result = ProcessRule(
            process_name=exe,
            target_mode=self.comboMode.currentText(),
            enabled=self.chkEnabled.isChecked(),
            description=self.txtDescription.text().strip(),
        )
        self.accept()

    def get_rule(self) -> Optional[ProcessRule]:
        return self._rule_result


class ProcessRulesDialog(QtWidgets.QDialog):
    """Main dialog displaying process automation rules and settings."""

    rules_changed = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, settings: Optional[QtCore.QSettings] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Process Auto-Switching Rules")
        self.resize(560, 420)
        self.setStyleSheet(DIALOG_STYLESHEET)

        self.settings = settings or QtCore.QSettings("github.com/morshedmilton/tcc-g15", "AWCC")
        self.rules: List[ProcessRule] = []
        self.auto_switch_enabled = True

        self._load_from_settings()

        # Layout
        mainLayout = QtWidgets.QVBoxLayout(self)
        mainLayout.setContentsMargins(12, 12, 12, 12)
        mainLayout.setSpacing(10)

        # Master Toggle
        topLayout = QtWidgets.QHBoxLayout()
        self.chkMaster = QtWidgets.QCheckBox("Enable Automatic Thermal Profile Switching")
        self.chkMaster.setChecked(self.auto_switch_enabled)
        self.chkMaster.toggled.connect(self._on_master_toggle)
        topLayout.addWidget(self.chkMaster)
        topLayout.addStretch(1)
        mainLayout.addLayout(topLayout)

        # Rules Table
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Executable", "Target Mode", "Enabled", "Description"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.itemChanged.connect(self._on_table_item_changed)
        mainLayout.addWidget(self.table)

        # Action Buttons
        btnLayout = QtWidgets.QHBoxLayout()
        btnAdd = QtWidgets.QPushButton("Add Rule")
        btnAdd.clicked.connect(self._on_add_rule)
        btnEdit = QtWidgets.QPushButton("Edit Rule")
        btnEdit.clicked.connect(self._on_edit_rule)
        btnRemove = QtWidgets.QPushButton("Remove Rule")
        btnRemove.setObjectName("RemoveBtn")
        btnRemove.clicked.connect(self._on_remove_rule)
        btnReset = QtWidgets.QPushButton("Reset to Defaults")
        btnReset.setObjectName("ResetBtn")
        btnReset.clicked.connect(self._on_reset_defaults)
        btnClose = QtWidgets.QPushButton("Close")
        btnClose.clicked.connect(self.accept)

        btnLayout.addWidget(btnAdd)
        btnLayout.addWidget(btnEdit)
        btnLayout.addWidget(btnRemove)
        btnLayout.addWidget(btnReset)
        btnLayout.addStretch(1)
        btnLayout.addWidget(btnClose)
        mainLayout.addLayout(btnLayout)

        self._populate_table()

    def _load_from_settings(self) -> None:
        """Load configured rules and toggle state from QSettings."""
        enabled_val = self.settings.value("auto_switch_enabled")
        if enabled_val is not None:
            self.auto_switch_enabled = str(enabled_val).lower() == "true"
        else:
            self.auto_switch_enabled = True

        raw_rules = self.settings.value("process_rules")
        loaded_rules: List[ProcessRule] = []
        if raw_rules:
            try:
                data = json.loads(str(raw_rules))
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            loaded_rules.append(ProcessRule.from_dict(item))
            except Exception:
                loaded_rules = []

        if not loaded_rules:
            loaded_rules = get_default_presets()

        self.rules = loaded_rules

    def _save_to_settings(self) -> None:
        """Persist current rules and toggle state to QSettings."""
        data = [r.to_dict() for r in self.rules]
        self.settings.setValue("process_rules", json.dumps(data))
        self.settings.setValue("auto_switch_enabled", self.auto_switch_enabled)
        self.rules_changed.emit()

    def _populate_table(self) -> None:
        """Populate the table widget with current rules."""
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.rules))
        for row, rule in enumerate(self.rules):
            # Executable
            item_exe = QtWidgets.QTableWidgetItem(rule.process_name)
            item_exe.setFlags(item_exe.flags() & ~QtCore.Qt.ItemIsEditable)

            # Target Mode
            item_mode = QtWidgets.QTableWidgetItem(rule.target_mode)
            item_mode.setFlags(item_mode.flags() & ~QtCore.Qt.ItemIsEditable)

            # Enabled Checkbox
            item_enabled = QtWidgets.QTableWidgetItem()
            item_enabled.setFlags(item_enabled.flags() | QtCore.Qt.ItemIsUserCheckable)
            item_enabled.setFlags(item_enabled.flags() & ~QtCore.Qt.ItemIsEditable)
            item_enabled.setCheckState(QtCore.Qt.Checked if rule.enabled else QtCore.Qt.Unchecked)

            # Description
            item_desc = QtWidgets.QTableWidgetItem(rule.description)
            item_desc.setFlags(item_desc.flags() & ~QtCore.Qt.ItemIsEditable)

            self.table.setItem(row, 0, item_exe)
            self.table.setItem(row, 1, item_mode)
            self.table.setItem(row, 2, item_enabled)
            self.table.setItem(row, 3, item_desc)

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.blockSignals(False)

    def _on_table_item_changed(self, item: QtWidgets.QTableWidgetItem) -> None:
        """Handle checkbox toggling directly inside table."""
        if item.column() == 2:
            row = item.row()
            if 0 <= row < len(self.rules):
                self.rules[row].enabled = (item.checkState() == QtCore.Qt.Checked)
                self._save_to_settings()

    def _on_master_toggle(self, checked: bool) -> None:
        self.auto_switch_enabled = checked
        self._save_to_settings()

    def _on_add_rule(self) -> None:
        dialog = RuleEditDialog(self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            new_rule = dialog.get_rule()
            if new_rule:
                # Replace if existing rule for same process, otherwise append
                existing_idx = next(
                    (i for i, r in enumerate(self.rules) if r.process_name == new_rule.process_name),
                    None,
                )
                if existing_idx is not None:
                    self.rules[existing_idx] = new_rule
                else:
                    self.rules.append(new_rule)
                self._save_to_settings()
                self._populate_table()

    def _on_edit_rule(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.rules):
            dialog = RuleEditDialog(self, rule=self.rules[row])
            if dialog.exec() == QtWidgets.QDialog.Accepted:
                updated = dialog.get_rule()
                if updated:
                    self.rules[row] = updated
                    self._save_to_settings()
                    self._populate_table()
        else:
            QtWidgets.QMessageBox.information(self, "Edit Rule", "Please select a rule from the table to edit.")

    def _on_remove_rule(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.rules):
            rule_name = self.rules[row].process_name
            res = QtWidgets.QMessageBox.question(
                self,
                "Confirm Removal",
                f"Remove rule for '{rule_name}'?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )
            if res == QtWidgets.QMessageBox.Yes:
                self.rules.pop(row)
                self._save_to_settings()
                self._populate_table()
        else:
            QtWidgets.QMessageBox.information(self, "Remove Rule", "Please select a rule from the table to remove.")

    def _on_reset_defaults(self) -> None:
        res = QtWidgets.QMessageBox.question(
            self,
            "Reset Presets",
            "Reset all process rules back to the 18 curated factory presets?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if res == QtWidgets.QMessageBox.Yes:
            self.rules = get_default_presets()
            self._save_to_settings()
            self._populate_table()
