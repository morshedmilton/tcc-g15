"""Adversarial Empirical Stress Testing for Cycle 006 OPP-008 Process-Aware Profile Switching.

This suite executes rigorous, adversarial failure-mode testing against:
1. Anti-Flapping Exit Hysteresis (4.0s / 2-cycle debounce, acoustic stability).
2. Concurrent Multi-Game Arbitration & Cooling Severity Priority Matrix.
3. Emergency Fail-Safe (INV-1) Supremacy Injection under active process rules.
4. Manual User Override Protection and state-preservation on exit.
5. Extended Adversarial Edge Cases:
   - Alternating Flapping Rapid Stress (10 cycles).
   - Staggered Multi-Game Re-entry under active baseline.
   - User Override Multi-Hop resilience.
   - Emergency Fail-Safe pre-emption over active user override.
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch
import pytest

from Backend.ProcessRule import ProcessRule
from GUI.AppGUI import TCC_GUI, ThermalMode
from GUI import HotKey


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


from GUI.TelemetryWorker import TelemetryWorker
from GUI.ProcessMonitorWorker import ProcessMonitorWorker


@pytest.fixture(autouse=True)
def mock_hotkey_and_watchdog():
    orig_hotkey = HotKey.HotKey.start
    orig_watchdog = TCC_GUI._startWatchdog
    orig_telemetry = TelemetryWorker.start
    orig_proc_mon = ProcessMonitorWorker.start
    HotKey.HotKey.start = lambda self: None
    TCC_GUI._startWatchdog = lambda self: None
    TelemetryWorker.start = lambda self: None
    ProcessMonitorWorker.start = lambda self: None
    yield
    HotKey.HotKey.start = orig_hotkey
    TCC_GUI._startWatchdog = orig_watchdog
    TelemetryWorker.start = orig_telemetry
    ProcessMonitorWorker.start = orig_proc_mon


@pytest.fixture(autouse=True)
def mock_toaster():
    with patch("GUI.AppGUI.TCC_GUI.toasterMessage", return_value=None), \
         patch("GUI.AppGUI.TCC_GUI._toasterMessageCurrentMode", return_value=None):
        yield


# ==============================================================================
# Adversarial Test 1: Anti-Flapping Hysteresis Stress Test
# ==============================================================================
def test_adversarial_1_anti_flapping_hysteresis_stress(qapp, mock_awcc):
    """Adversarial Test 1: Anti-Flapping Hysteresis Stress Test.

    - Simulate a monitored game (cyberpunk2077.exe) disappearing for 1 cycle (2.5s)
      and reappearing. Assert that mode NEVER reverts or flaps.
    - Simulate disappearing for 2 cycles (5.0s > 4.0s debounce). Assert that mode
      cleanly reverts to _baselineMode.
    """
    window = TCC_GUI(mock_awcc)
    try:
        # Initial baseline mode is Quiet
        window._modeSwitch.setChecked(ThermalMode.Quiet.value)
        window._autoSwitchEnabled = True
        window._processRules = [
            ProcessRule("cyberpunk2077.exe", "G_Mode", enabled=True, description="Cyberpunk 2077")
        ]

        # 1. Monitored game launches -> switches to G_Mode, records Quiet as baseline
        window._onProcessesScanned({"cyberpunk2077.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.G_Mode.value
        assert window._baselineMode == ThermalMode.Quiet.value
        assert window._missingCycles.get("cyberpunk2077.exe") == 0

        # Spy on setChecked calls to ensure zero mode-flapping occurs
        mode_transitions: list[str] = []
        orig_setChecked = window._modeSwitch.setChecked

        def tracking_setChecked(val):
            mode_transitions.append(val)
            orig_setChecked(val)

        window._modeSwitch.setChecked = tracking_setChecked

        # 2. Simulate game disappearing for 1 cycle (2.5s < 4.0s debounce threshold)
        window._onProcessesScanned(set())
        assert window._modeSwitch.getChecked() == ThermalMode.G_Mode.value
        assert window._baselineMode == ThermalMode.Quiet.value
        assert window._missingCycles.get("cyberpunk2077.exe") == 1
        # Crucial assertion: setChecked was NOT called during 1-cycle absence
        assert len(mode_transitions) == 0, f"Mode flapped unexpectedly during 1-cycle disappearance: {mode_transitions}"

        # 3. Game reappears in scan cycle
        window._onProcessesScanned({"cyberpunk2077.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.G_Mode.value
        assert window._baselineMode == ThermalMode.Quiet.value
        assert window._missingCycles.get("cyberpunk2077.exe") == 0
        assert len(mode_transitions) == 0, f"Mode flapped unexpectedly upon game re-emergence: {mode_transitions}"

        # 4. Now simulate game disappearing for 2 full consecutive cycles (5.0s > 4.0s debounce)
        # Cycle 1 absent:
        window._onProcessesScanned(set())
        assert window._modeSwitch.getChecked() == ThermalMode.G_Mode.value
        assert window._baselineMode == ThermalMode.Quiet.value
        assert window._missingCycles.get("cyberpunk2077.exe") == 1
        assert len(mode_transitions) == 0

        # Cycle 2 absent (debounce timer elapsed):
        window._onProcessesScanned(set())
        assert window._modeSwitch.getChecked() == ThermalMode.Quiet.value
        assert window._baselineMode is None
        assert "cyberpunk2077.exe" not in window._missingCycles
        assert mode_transitions == [ThermalMode.Quiet.value], (
            f"Expected exactly 1 transition back to baseline Quiet, got: {mode_transitions}"
        )
    finally:
        window._destroy()


# ==============================================================================
# Adversarial Test 2: Concurrent Multi-Game Arbitration & Cooling Severity Priority
# ==============================================================================
def test_adversarial_2_concurrent_multigame_arbitration_cooling_severity(qapp, mock_awcc):
    """Adversarial Test 2: Concurrent Multi-Game Arbitration & Cooling Severity Priority.

    - Simulate gta5.exe (Performance) launching while in Quiet mode. Assert mode -> Performance.
    - While gta5.exe is still running, simulate cyberpunk2077.exe (G-Mode) launching. Assert mode -> G_Mode.
    - Simulate cyberpunk2077.exe exiting. Assert mode reverts to Performance (since gta5.exe is still active).
    - Simulate gta5.exe exiting. Assert mode reverts to Quiet (the original baseline).
    """
    window = TCC_GUI(mock_awcc)
    try:
        # Starting baseline mode: Quiet
        window._modeSwitch.setChecked(ThermalMode.Quiet.value)
        window._autoSwitchEnabled = True
        window._processRules = [
            ProcessRule("gta5.exe", "Performance", enabled=True, description="GTA V"),
            ProcessRule("cyberpunk2077.exe", "G_Mode", enabled=True, description="Cyberpunk 2077"),
        ]

        # Step 1: gta5.exe launches while in Quiet mode
        window._onProcessesScanned({"gta5.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.Performance.value
        assert window._baselineMode == ThermalMode.Quiet.value

        # Step 2: While gta5.exe is still running, cyberpunk2077.exe launches
        # Cooling Severity Priority: G_Mode (5) > Performance (4)
        window._onProcessesScanned({"gta5.exe", "cyberpunk2077.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.G_Mode.value
        # Baseline MUST remain Quiet (must NOT be overwritten with Performance!)
        assert window._baselineMode == ThermalMode.Quiet.value

        # Step 3: cyberpunk2077.exe exits; gta5.exe remains active
        # Scan 1: cyberpunk missing cycle 1 (< 2 cycles debounce) -> remains G_Mode
        window._onProcessesScanned({"gta5.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.G_Mode.value
        assert window._baselineMode == ThermalMode.Quiet.value

        # Scan 2: cyberpunk missing cycle 2 (>= 2 cycles debounce) -> cyberpunk pruned
        # gta5.exe is still active -> mode reverts to Performance
        window._onProcessesScanned({"gta5.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.Performance.value
        assert window._baselineMode == ThermalMode.Quiet.value

        # Step 4: gta5.exe terminates
        # Scan 1: gta5 missing cycle 1 (< 2 cycles debounce) -> remains Performance
        window._onProcessesScanned(set())
        assert window._modeSwitch.getChecked() == ThermalMode.Performance.value
        assert window._baselineMode == ThermalMode.Quiet.value

        # Scan 2: gta5 missing cycle 2 (>= 2 cycles debounce) -> gta5 pruned
        # All games terminated -> reverts to original Quiet baseline
        window._onProcessesScanned(set())
        assert window._modeSwitch.getChecked() == ThermalMode.Quiet.value
        assert window._baselineMode is None
    finally:
        window._destroy()


# ==============================================================================
# Adversarial Test 3: Emergency Fail-Safe (INV-1) Injection under Active Rule
# ==============================================================================
def test_adversarial_3_emergency_failsafe_inv1_injection_under_active_rule(qapp, mock_awcc):
    """Adversarial Test 3: Emergency Fail-Safe (INV-1) Injection under Active Rule.

    - Simulate active game rule (Performance).
    - Inject simulated emergency thermal excursion (CPU >= 101°C).
    - Assert G_Mode triggers immediately via hard fail-safe.
    - While fail-safe is engaged, simulate game exiting.
    - Assert that baseline restoration is STRICTLY SUPPRESSED and mode remains G_Mode
      until fail-safe cooldown completes.
    """
    window = TCC_GUI(mock_awcc)
    try:
        # Starting in Balanced mode
        window._modeSwitch.setChecked(ThermalMode.Balanced.value)
        window._autoSwitchEnabled = True
        window._processRules = [
            ProcessRule("gta5.exe", "Performance", enabled=True, description="GTA V")
        ]

        # Step 1: Simulate active game rule -> switches to Performance
        window._onProcessesScanned({"gta5.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.Performance.value
        assert window._baselineMode == ThermalMode.Balanced.value

        # Step 2: Inject emergency thermal excursion (CPU = 101°C >= FAILSAFE_HARD_CPU_TEMP 100°C)
        mock_awcc.getFanRelatedTemp.side_effect = lambda idx: 60 if idx == mock_awcc.GPUFanIdx else 101
        window._gpuTemp.read = MagicMock(return_value=60)

        # Initial reading registers excursion
        window._updateAppState()
        # Backdate hard temp excursion start timestamp to exceed hard trigger delay
        window._failsafeHardTempStartTs = time.time() - (window.FAILSAFE_HARD_TRIGGER_DELAY_SEC + 1.0)
        window._updateAppState()

        # Hard fail-safe MUST trigger immediately to G_Mode
        assert window._modeSwitch.getChecked() == ThermalMode.G_Mode.value
        assert window._failsafeTrippedPrevModeStr == ThermalMode.Performance.value

        # Step 3: While fail-safe is engaged, simulate game exiting across multiple scan cycles
        # Scans with empty process set
        for _ in range(5):
            window._onProcessesScanned(set())
            # Mode MUST remain locked in G_Mode; baseline restoration is strictly suppressed!
            assert window._modeSwitch.getChecked() == ThermalMode.G_Mode.value, (
                "SAFETY VIOLATION: Baseline restoration disrupted emergency G_Mode fail-safe cooling!"
            )
            assert window._failsafeTrippedPrevModeStr == ThermalMode.Performance.value

        # Step 4: Simulate thermal recovery & cooldown expiration
        # Return temperatures to safe operating levels (CPU 50°C, GPU 45°C)
        mock_awcc.getFanRelatedTemp.side_effect = lambda idx: 45 if idx == mock_awcc.GPUFanIdx else 50
        window._gpuTemp.read = MagicMock(return_value=45)

        # Backdate cooldown timestamp past FAILSAFE_RESET_AFTER_TEMP_IS_OK_FOR_SEC (60s)
        window._failsafeTempIsHighTs = time.time() - (window.FAILSAFE_RESET_AFTER_TEMP_IS_OK_FOR_SEC + 5.0)

        # Trigger fail-safe state evaluation -> resets fail-safe trip to prev mode (Performance)
        window._updateAppState()
        assert window._failsafeTrippedPrevModeStr is None
        assert window._modeSwitch.getChecked() == ThermalMode.Performance.value

        # Step 5: After fail-safe cooldown completes, game exit debounce elapses and restores baseline
        window._onProcessesScanned(set())
        window._onProcessesScanned(set())
        assert window._modeSwitch.getChecked() == ThermalMode.Balanced.value
        assert window._baselineMode is None
    finally:
        window._destroy()


def test_adversarial_defect_failsafe_corrupts_user_override(qapp, mock_awcc):
    """DEFECT REPRODUCTION: Fail-Safe Trip Inadvertently Sets _userOverride=True.

    Root Cause Analysis:
    In AppGUI.py line 742 & 750, self._modeSwitch.setChecked() is called during fail-safe
    trip and recovery without setting self._inAutoSwitch = True.
    Consequently, onModeChange (line 630) detects _inAutoSwitch=False with _baselineMode != None,
    falsely flagging self._userOverride = True.
    When the game subsequently terminates, the expected baseline restoration (Balanced) is
    suppressed because the state machine believes the user explicitly selected Performance!
    """
    window = TCC_GUI(mock_awcc)
    try:
        window._modeSwitch.setChecked(ThermalMode.Balanced.value)
        window._autoSwitchEnabled = True
        window._processRules = [ProcessRule("gta5.exe", "Performance")]

        # 1. Game launches -> Performance, baseline = Balanced
        window._onProcessesScanned({"gta5.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.Performance.value
        assert window._baselineMode == ThermalMode.Balanced.value
        assert window._userOverride is False

        # 2. Emergency thermal excursion triggers INV-1 hard fail-safe
        mock_awcc.getFanRelatedTemp.side_effect = lambda idx: 60 if idx == mock_awcc.GPUFanIdx else 101
        window._gpuTemp.read = MagicMock(return_value=60)
        window._updateAppState()
        window._failsafeHardTempStartTs = time.time() - (window.FAILSAFE_HARD_TRIGGER_DELAY_SEC + 1.0)
        window._updateAppState()

        assert window._modeSwitch.getChecked() == ThermalMode.G_Mode.value
        assert window._failsafeTrippedPrevModeStr == ThermalMode.Performance.value

        # BUG ASSERTION: Hard fail-safe trip MUST NOT flag user override!
        # The user did NOT click GUI or press G-Key.
        assert window._userOverride is False, (
            "DEFECT CONFIRMED: Fail-safe trip leaked into _userOverride! onModeChange() "
            "treated emergency G_Mode trip as a user manual selection."
        )

        # 3. Game exits during trip
        window._onProcessesScanned(set())
        window._onProcessesScanned(set())

        # 4. Fail-safe cooldown completes
        mock_awcc.getFanRelatedTemp.side_effect = lambda idx: 45 if idx == mock_awcc.GPUFanIdx else 50
        window._gpuTemp.read = MagicMock(return_value=45)
        window._failsafeTempIsHighTs = time.time() - (window.FAILSAFE_RESET_AFTER_TEMP_IS_OK_FOR_SEC + 5.0)
        window._updateAppState()

        # 5. Process scan processes exit debounce
        window._onProcessesScanned(set())
        window._onProcessesScanned(set())

        # Baseline Balanced MUST be restored, but is lost if _userOverride was set!
        assert window._modeSwitch.getChecked() == ThermalMode.Balanced.value
        assert window._baselineMode is None
    finally:
        window._destroy()


# ==============================================================================
# Adversarial Test 4: Manual User Override Protection
# ==============================================================================
def test_adversarial_4_manual_user_override_protection(qapp, mock_awcc):
    """Adversarial Test 4: Manual User Override Protection.

    - While game is active and system switched to Performance, simulate user clicking Balanced.
    - Assert _userOverride = True and mode stays Balanced on subsequent scans as long as game runs.
    - When game exits, assert _userOverride resets to False without disrupting user's manually chosen mode.
    """
    window = TCC_GUI(mock_awcc)
    try:
        # Starting in Quiet mode
        window._modeSwitch.setChecked(ThermalMode.Quiet.value)
        window._autoSwitchEnabled = True
        window._processRules = [
            ProcessRule("gta5.exe", "Performance", enabled=True, description="GTA V")
        ]

        # Step 1: Game launches -> automatic switch to Performance
        window._onProcessesScanned({"gta5.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.Performance.value
        assert window._baselineMode == ThermalMode.Quiet.value
        assert window._userOverride is False

        # Step 2: User explicitly overrides mode to Balanced via UI click
        window._modeSwitch.setChecked(ThermalMode.Balanced.value)
        assert window._userOverride is True
        assert window._modeSwitch.getChecked() == ThermalMode.Balanced.value

        # Step 3: Subsequent scans while game continues to run MUST NOT revert to Performance
        for _ in range(4):
            window._onProcessesScanned({"gta5.exe"})
            assert window._modeSwitch.getChecked() == ThermalMode.Balanced.value, (
                "User override was clobbered by automatic process scan!"
            )
            assert window._userOverride is True
            assert window._baselineMode == ThermalMode.Quiet.value

        # Step 4: Game exits
        # Cycle 1 absent (< 2 cycles debounce)
        window._onProcessesScanned(set())
        assert window._modeSwitch.getChecked() == ThermalMode.Balanced.value
        assert window._userOverride is True

        # Cycle 2 absent (debounce expired)
        window._onProcessesScanned(set())
        # Assert _userOverride resets to False
        assert window._userOverride is False
        assert window._baselineMode is None
        # Assert user's manually chosen mode (Balanced) is PRESERVED, not forced to Quiet
        assert window._modeSwitch.getChecked() == ThermalMode.Balanced.value
    finally:
        window._destroy()


# ==============================================================================
# Extended Adversarial Stress Cases
# ==============================================================================
def test_adversarial_extended_rapid_alternating_flapping_stress(qapp, mock_awcc):
    """Stress Test: 10 consecutive cycles of rapid 1-cycle flapping (process toggling on/off).

    Ensures that rapid flapping does not degrade internal debounce state or leak mode transitions.
    """
    window = TCC_GUI(mock_awcc)
    try:
        window._modeSwitch.setChecked(ThermalMode.Balanced.value)
        window._autoSwitchEnabled = True
        window._processRules = [ProcessRule("cs2.exe", "Performance")]

        # Launch
        window._onProcessesScanned({"cs2.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.Performance.value
        assert window._baselineMode == ThermalMode.Balanced.value

        # Track any unauthorized setChecked calls
        transitions = []
        orig_setChecked = window._modeSwitch.setChecked

        def tracking_setChecked(val):
            transitions.append(val)
            orig_setChecked(val)

        window._modeSwitch.setChecked = tracking_setChecked

        # Rapidly toggle presence over 10 cycles (present, absent, present, absent...)
        for i in range(10):
            if i % 2 == 0:
                window._onProcessesScanned(set())  # absent for 1 cycle
                assert window._missingCycles.get("cs2.exe") == 1
            else:
                window._onProcessesScanned({"cs2.exe"})  # reappears
                assert window._missingCycles.get("cs2.exe") == 0

            assert window._modeSwitch.getChecked() == ThermalMode.Performance.value
            assert window._baselineMode == ThermalMode.Balanced.value

        # Must have had ZERO extraneous mode transitions
        assert len(transitions) == 0, f"Unstable mode transitions detected: {transitions}"
    finally:
        window._destroy()


def test_adversarial_extended_user_override_double_hop(qapp, mock_awcc):
    """Stress Test: User changes mode twice during game session (Performance -> Balanced -> Quiet).

    When game closes, final chosen mode (Quiet) must persist and override flags reset cleanly.
    """
    window = TCC_GUI(mock_awcc)
    try:
        window._modeSwitch.setChecked(ThermalMode.Balanced.value)
        window._autoSwitchEnabled = True
        window._processRules = [ProcessRule("cs2.exe", "Performance")]

        window._onProcessesScanned({"cs2.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.Performance.value
        assert window._baselineMode == ThermalMode.Balanced.value

        # User hops to Custom
        window._modeSwitch.setChecked(ThermalMode.Custom.value)
        assert window._userOverride is True
        assert window._modeSwitch.getChecked() == ThermalMode.Custom.value

        # User hops to Quiet
        window._modeSwitch.setChecked(ThermalMode.Quiet.value)
        assert window._userOverride is True
        assert window._modeSwitch.getChecked() == ThermalMode.Quiet.value

        # Scan while running
        window._onProcessesScanned({"cs2.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.Quiet.value

        # Game terminates after debounce
        window._onProcessesScanned(set())
        window._onProcessesScanned(set())
        assert window._userOverride is False
        assert window._baselineMode is None
        assert window._modeSwitch.getChecked() == ThermalMode.Quiet.value
    finally:
        window._destroy()


def test_adversarial_extended_failsafe_overrides_active_user_override(qapp, mock_awcc):
    """Stress Test: Critical thermal excursion must override even manual user override (INV-1 supremacy)."""
    window = TCC_GUI(mock_awcc)
    try:
        window._modeSwitch.setChecked(ThermalMode.Quiet.value)
        window._autoSwitchEnabled = True
        window._processRules = [ProcessRule("cs2.exe", "Performance")]

        # Launch game -> Performance
        window._onProcessesScanned({"cs2.exe"})
        assert window._modeSwitch.getChecked() == ThermalMode.Performance.value

        # User overrides to Quiet
        window._modeSwitch.setChecked(ThermalMode.Quiet.value)
        assert window._userOverride is True
        assert window._modeSwitch.getChecked() == ThermalMode.Quiet.value

        # Thermal excursion: CPU = 102°C
        mock_awcc.getFanRelatedTemp.side_effect = lambda idx: 55 if idx == mock_awcc.GPUFanIdx else 102
        window._gpuTemp.read = MagicMock(return_value=55)

        window._updateAppState()
        window._failsafeHardTempStartTs = time.time() - (window.FAILSAFE_HARD_TRIGGER_DELAY_SEC + 1.0)
        window._updateAppState()

        # Hard fail-safe MUST force G_Mode regardless of active user override!
        assert window._modeSwitch.getChecked() == ThermalMode.G_Mode.value
        assert window._failsafeTrippedPrevModeStr == ThermalMode.Quiet.value
    finally:
        window._destroy()
