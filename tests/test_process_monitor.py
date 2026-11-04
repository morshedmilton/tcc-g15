"""Multi-Level Automated QA & Safety Verification for OPP-008 Process Automation & Defect Fixes.

Covers REQ-0601 through REQ-0608:
- Process Detection Engine & secondary thread scanning (REQ-0601 / DEF-009)
- Dynamic Rule Matching, Cooling Severity Matrix & State Restoration (REQ-0602)
- Anti-Flapping Exit Hysteresis (4.0s debounce) (REQ-0603)
- Curated Presets Catalog & Defaults (18 presets) (REQ-0604)
- Rule Management UI & QSettings Persistence (REQ-0605)
- Unconditional INV-1 Hard Fail-Safe Supremacy Lockout (REQ-0606 / DEF-008)
- Diagnostics Privacy Redaction for PII (REQ-0607 / DEF-006)
- Supply Chain Production Pinned Dependency psutil==7.2.2 (REQ-0608 / DEF-007)
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from PySide6 import QtCore, QtWidgets

from Backend.ProcessRule import ProcessRule, COOLING_SEVERITY_ORDER
from Backend.ProcessRulePresets import get_default_presets
from GUI.ProcessMonitorWorker import ProcessMonitorWorker
from GUI.ProcessRulesDialog import ProcessRulesDialog
from GUI.AppGUI import TCC_GUI, ThermalMode, APP_STYLESHEET
from GUI import Diagnostics, HotKey


@pytest.fixture
def qapp():
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication([])
    return app


@pytest.fixture
def mock_awcc():
    awcc = MagicMock()
    awcc.GPUFanIdx = 0
    awcc.CPUFanIdx = 1
    awcc.Mode.Custom = 0
    awcc.Mode.Balanced = 1
    awcc.Mode.Performance = 2
    awcc.Mode.Quiet = 3
    awcc.Mode.G_Mode = 4
    awcc.setMode.return_value = True
    awcc.getFanRelatedTemp.return_value = 50
    awcc.getFanRPM.return_value = 2000
    return awcc


@pytest.fixture(autouse=True)
def mock_detect_hardware():
    class DummyDetectHardware:
        GPUFanIdx = 0
        CPUFanIdx = 1

        def getHardwareName(self, idx):
            return "Test Device"

        def getModelName(self):
            return "Dell G15 5530"

    with patch("GUI.AppGUI.DetectHardware", DummyDetectHardware):
        yield


@pytest.fixture(autouse=True)
def mock_hotkey_and_watchdog():
    orig_hotkey = HotKey.HotKey.start
    orig_watchdog = TCC_GUI._startWatchdog
    HotKey.HotKey.start = lambda self: None
    TCC_GUI._startWatchdog = lambda self: None
    yield
    HotKey.HotKey.start = orig_hotkey
    TCC_GUI._startWatchdog = orig_watchdog


@pytest.fixture(autouse=True)
def mock_toaster():
    with patch("GUI.AppGUI.TCC_GUI.toasterMessage", return_value=None), \
         patch("GUI.AppGUI.TCC_GUI._toasterMessageCurrentMode", return_value=None):
        yield


def test_process_monitor_scanning_and_signal(qapp):
    """REQ-0601: ProcessMonitorWorker operates non-invasively, handles exceptions and emits lowercase names."""
    worker = ProcessMonitorWorker(interval_ms=100)

    # 1. Verify safe exception trapping with mock processes
    mock_p1 = MagicMock()
    mock_p1.info = {"name": "Cs2.EXE"}

    mock_p2 = MagicMock()
    type(mock_p2).info = property(lambda self: (_ for _ in ()).throw(Exception("Permission denied")))

    mock_p3 = MagicMock()
    mock_p3.info = {"name": "Blender.exe"}

    with patch("psutil.process_iter", return_value=[mock_p1, mock_p2, mock_p3]):
        scanned = worker.scan_once()
        assert "cs2.exe" in scanned
        assert "blender.exe" in scanned
        assert len(scanned) == 2

    # 2. Verify Qt signal emission
    received = []
    worker.processes_scanned.connect(lambda s: received.append(s))
    with patch("psutil.process_iter", return_value=[mock_p1]):
        worker._on_timer_tick()
        assert len(received) == 0  # not running yet

        worker._running = True
        worker._on_timer_tick()
        assert len(received) == 1
        assert "cs2.exe" in received[0]

    # 3. Test lifecycle
    worker.stop()
    assert worker._running is False


def test_dynamic_rule_matching_priority_and_restoration(qapp, mock_awcc):
    """REQ-0602: Dynamic rule matching, Cooling Severity Priority Matrix, and baseline restoration."""
    # Test ProcessRule comparison based on Cooling Severity Matrix:
    # G_Mode (5) > Performance (4) > Custom (3) > Balanced (2) > Quiet (1)
    r_quiet = ProcessRule("notepad.exe", "Quiet")
    r_balanced = ProcessRule("calc.exe", "Balanced")
    r_custom = ProcessRule("code.exe", "Custom")
    r_perf = ProcessRule("cs2.exe", "Performance")
    r_gmode = ProcessRule("cyberpunk2077.exe", "G_Mode")

    assert r_gmode > r_perf > r_custom > r_balanced > r_quiet
    assert r_quiet < r_balanced
    assert COOLING_SEVERITY_ORDER["G_Mode"] == 5

    window = TCC_GUI(mock_awcc)
    try:
        window._modeSwitch.setChecked(ThermalMode.Balanced.value)
        window._autoSwitchEnabled = True
        window._processRules = [
            ProcessRule("cs2.exe", "Performance"),
            ProcessRule("cyberpunk2077.exe", "G_Mode"),
            ProcessRule("word.exe", "Quiet"),
        ]

        # 1. 0-to-1 match transition: launches cs2.exe -> should switch to Performance, save Balanced as baseline
        assert window._baselineMode is None
        window._onProcessesScanned({"cs2.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.Performance.value
        assert window._baselineMode == ThermalMode.Balanced.value

        # 2. Multi-process priority arbitration: launches cyberpunk2077.exe alongside cs2.exe
        # G_Mode > Performance, so system must switch to G_Mode while keeping original baseline
        window._onProcessesScanned({"cs2.exe", "cyberpunk2077.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.G_Mode.value
        assert window._baselineMode == ThermalMode.Balanced.value  # MUST NOT be overwritten!

        # 3. Cyberpunk terminates, cs2 remains
        # Should drop from G_Mode to Performance
        window._onProcessesScanned({"cs2.exe"})  # cyberpunk missing cycle 1
        window._onProcessesScanned({"cs2.exe"})  # cyberpunk missing cycle 2 (pruned)
        assert window._modeSwitch.getChecked() == ThermalMode.Performance.value
        assert window._baselineMode == ThermalMode.Balanced.value

        # 4. CS2 terminates -> after debounce, restores Balanced baseline
        window._onProcessesScanned(set())  # missing cycle 1
        assert window._modeSwitch.getChecked() == ThermalMode.Performance.value
        window._onProcessesScanned(set())  # missing cycle 2 -> debounce complete
        assert window._modeSwitch.getChecked() == ThermalMode.Balanced.value
        assert window._baselineMode is None
    finally:
        window._destroy()


def test_manual_user_override(qapp, mock_awcc):
    """REQ-0602: Manual mode adjustments during an active rule session set _userOverride and suppress auto-switching."""
    window = TCC_GUI(mock_awcc)
    try:
        window._modeSwitch.setChecked(ThermalMode.Balanced.value)
        window._autoSwitchEnabled = True
        window._processRules = [ProcessRule("cs2.exe", "Performance")]

        # Process launches -> switches to Performance
        window._onProcessesScanned({"cs2.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.Performance.value
        assert window._baselineMode == ThermalMode.Balanced.value
        assert window._userOverride is False

        # User explicitly overrides mode to Quiet via UI
        window._modeSwitch.setChecked(ThermalMode.Quiet.value)
        assert window._userOverride is True

        # Subsequent scan cycles MUST NOT revert to Performance while user override is active
        window._onProcessesScanned({"cs2.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.Quiet.value

        # When process exits and debounce expires, user override clears but chosen mode is retained
        window._onProcessesScanned(set())
        window._onProcessesScanned(set())
        assert window._userOverride is False
        assert window._baselineMode is None
        assert window._modeSwitch.getChecked() == ThermalMode.Quiet.value
    finally:
        window._destroy()


def test_anti_flapping_exit_hysteresis(qapp, mock_awcc):
    """REQ-0603: 4.0-second (2-cycle) debounce prevents acoustic fan cycling on transient absence."""
    window = TCC_GUI(mock_awcc)
    try:
        window._modeSwitch.setChecked(ThermalMode.Balanced.value)
        window._autoSwitchEnabled = True
        window._processRules = [ProcessRule("cs2.exe", "Performance")]

        # Launch
        window._onProcessesScanned({"cs2.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.Performance.value

        # Missing 1 cycle (< 4.0s debounce) -> must maintain Performance
        window._onProcessesScanned(set())
        assert window._modeSwitch.getChecked() == ThermalMode.Performance.value
        assert window._missingCycles.get("cs2.exe") == 1

        # Process reappears within debounce window -> reset counter and retain mode
        window._onProcessesScanned({"cs2.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.Performance.value
        assert window._missingCycles.get("cs2.exe") == 0

        # Process gone for 2 full consecutive cycles (>= 4.0s) -> triggers restoration
        window._onProcessesScanned(set())
        assert window._modeSwitch.getChecked() == ThermalMode.Performance.value
        window._onProcessesScanned(set())
        assert window._modeSwitch.getChecked() == ThermalMode.Balanced.value
    finally:
        window._destroy()


def test_curated_presets_catalog_and_defaults():
    """REQ-0604: Curated presets catalog contains exactly 18 default rules matching SRC-009."""
    presets = get_default_presets()
    assert len(presets) == 18

    # All enabled by default
    assert all(r.enabled for r in presets)

    # Validate key targets from SRC-009
    rule_map = {r.process_name: r for r in presets}

    # AAA Gaming
    assert rule_map["cyberpunk2077.exe"].target_mode == "G_Mode"
    assert rule_map["gta5.exe"].target_mode == "Performance"
    assert rule_map["rdr2.exe"].target_mode == "G_Mode"
    assert rule_map["eldenring.exe"].target_mode == "Performance"
    assert rule_map["bg3.exe"].target_mode == "Performance"

    # Alias matching for Baldur's Gate 3 DirectX 11
    assert rule_map["bg3.exe"].matches("bg3_dx11.exe")
    assert rule_map["bg3.exe"].matches("bg3.exe")

    # Competitive Esports
    assert rule_map["cs2.exe"].target_mode == "Performance"
    assert rule_map["r5apex.exe"].target_mode == "Performance"
    assert rule_map["valorant-win64-shipping.exe"].target_mode == "Performance"
    assert rule_map["fortniteclient-win64-shipping.exe"].target_mode == "Performance"
    assert rule_map["overwatch.exe"].target_mode == "Performance"
    assert rule_map["cod.exe"].target_mode == "G_Mode"

    # Content Creation & Benchmarks
    assert rule_map["blender.exe"].target_mode == "Performance"
    assert rule_map["premiere.exe"].target_mode == "Performance"
    assert rule_map["afterfx.exe"].target_mode == "Performance"
    assert rule_map["resolve.exe"].target_mode == "Performance"
    assert rule_map["handbrake.exe"].target_mode == "Performance"
    assert rule_map["cinebench.exe"].target_mode == "G_Mode"
    assert rule_map["3dmark.exe"].target_mode == "G_Mode"


def test_rules_persistence_qsettings(qapp, tmp_path):
    """REQ-0605: QSettings serialization and rule management dialog."""
    ini_file = str(tmp_path / "test_settings.ini")
    test_settings = QtCore.QSettings(ini_file, QtCore.QSettings.IniFormat)

    # Initial state should load presets
    dialog = ProcessRulesDialog(settings=test_settings)
    assert len(dialog.rules) == 18
    assert dialog.auto_switch_enabled is True

    # Modify master toggle
    dialog.chkMaster.setChecked(False)
    assert test_settings.value("auto_switch_enabled") in (False, "false")

    # Add custom rule
    new_rule = ProcessRule("mygame.exe", "Performance", True, "My Game")
    dialog.rules.append(new_rule)
    dialog._save_to_settings()

    # Re-instantiate from settings to verify persistence
    dialog2 = ProcessRulesDialog(settings=test_settings)
    assert len(dialog2.rules) == 19
    assert any(r.process_name == "mygame.exe" for r in dialog2.rules)

    # Reset to defaults
    with patch("PySide6.QtWidgets.QMessageBox.question", return_value=QtWidgets.QMessageBox.Yes):
        dialog2._on_reset_defaults()
        assert len(dialog2.rules) == 18
        assert not any(r.process_name == "mygame.exe" for r in dialog2.rules)


def test_inv1_hard_failsafe_supremacy_over_rules(qapp, mock_awcc):
    """REQ-0606 / DEF-008: Hard fail-safe trip locks out all process rule profile changes."""
    window = TCC_GUI(mock_awcc)
    try:
        window._autoSwitchEnabled = True
        window._processRules = [
            ProcessRule("cs2.exe", "Performance"),
            ProcessRule("quietapp.exe", "Quiet"),
        ]

        # Simulate hard fail-safe trip engaged (INV-1 forces G-Mode)
        window._failsafeTrippedPrevModeStr = ThermalMode.Balanced.value
        window._modeSwitch.setChecked(ThermalMode.G_Mode.value)

        # Process scanning with rule that wants Performance or Quiet
        # MUST BE COMPLETELY LOCKED OUT while fail-safe is tripped
        window._onProcessesScanned({"quietapp.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.G_Mode.value

        window._onProcessesScanned({"cs2.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.G_Mode.value

        # Process termination while fail-safe active must not downgrade mode
        window._onProcessesScanned(set())
        window._onProcessesScanned(set())
        assert window._modeSwitch.getChecked() == ThermalMode.G_Mode.value
    finally:
        window._destroy()


def test_diagnostics_privacy_redaction_def006(tmp_path, monkeypatch):
    """REQ-0607 / DEF-006: Diagnostics redaction strips UserName, PrimaryOwnerName, DNSHostName."""
    class FakeInst:
        properties = ["Model", "UserName", "PrimaryOwnerName", "DNSHostName", "Domain", "SerialNumber"]
        Model = "Dell G15 5530"
        UserName = "CORP\\alice"
        PrimaryOwnerName = "alice@corp.com"
        DNSHostName = "alice-workstation"
        Domain = "CORP"
        SerialNumber = "SECRET123"

    class FakeWmi:
        def Win32_ComputerSystem(self):
            return [FakeInst()]

    monkeypatch.setattr("wmi.WMI", lambda: FakeWmi())
    monkeypatch.setattr(Diagnostics, "_awccDump", lambda: {})

    wmi_data = Diagnostics._wmi(("Win32_ComputerSystem",))
    cs_rows = wmi_data.get("Win32_ComputerSystem", [])
    assert len(cs_rows) == 1
    row = cs_rows[0]

    # Verify PII fields are strictly redacted
    assert row.get("UserName") == "[REDACTED]"
    assert row.get("PrimaryOwnerName") == "[REDACTED]"
    assert row.get("DNSHostName") == "[REDACTED]"
    assert row.get("Domain") == "[REDACTED]"
    assert "SerialNumber" not in row  # skipped entirely

    # Build full bundle and verify zip contains zero leaked PII strings
    zip_path, _ = Diagnostics.build("TCC Test", "1.8.6")
    assert zip_path is not None
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            with z.open("wmi.json") as f:
                content = f.read().decode("utf-8")
                assert "CORP\\alice" not in content
                assert "alice@corp.com" not in content
                assert "alice-workstation" not in content
                assert "[REDACTED]" in content
    finally:
        Path(zip_path).unlink(missing_ok=True)


def test_psutil_pinned_dependency():
    """REQ-0608 / DEF-007: psutil==7.2.2 is pinned in requirements.txt and imports correctly."""
    req_file = Path("requirements.txt")
    assert req_file.exists()
    content = req_file.read_text(encoding="utf-8")
    assert "psutil==7.2.2" in content

    import psutil
    assert psutil.__version__ == "7.2.2"
