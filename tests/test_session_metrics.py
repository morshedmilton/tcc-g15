import json
import time
import zipfile
from unittest.mock import MagicMock, patch
from PySide6 import QtWidgets
from Backend.SessionMetricsTracker import SessionMetricsTracker, get_session_tracker, set_session_tracker
from Backend.TelemetryTypes import TelemetrySnapshot
from GUI.AppGUI import TCC_GUI, ThermalMode
from GUI.HotKey import HotKey
import GUI.Diagnostics as Diagnostics


def test_tracker_peaks_and_averages():
    tracker = SessionMetricsTracker(start_ts=1000.0)

    # Sample 1: 50°C CPU, 45°C GPU, 1500 RPM
    tracker.update(TelemetrySnapshot(cpu_temp=50, gpu_temp=45, cpu_rpm=1500, gpu_rpm=1600, is_ac_power=True, timestamp=1001.0))
    # Sample 2: 85°C CPU, 75°C GPU, 3200 RPM
    tracker.update(TelemetrySnapshot(cpu_temp=85, gpu_temp=75, cpu_rpm=3200, gpu_rpm=3000, is_ac_power=True, timestamp=1003.0))
    # Sample 3: 70°C CPU, 60°C GPU, 2400 RPM
    tracker.update(TelemetrySnapshot(cpu_temp=70, gpu_temp=60, cpu_rpm=2400, gpu_rpm=2200, is_ac_power=True, timestamp=1005.0))

    summary = tracker.get_summary()

    assert summary["sample_count"] == 3
    assert summary["peak_cpu_temp"] == 85
    assert summary["min_cpu_temp"] == 50
    assert summary["avg_cpu_temp"] == round((50 + 85 + 70) / 3, 1)

    assert summary["peak_gpu_temp"] == 75
    assert summary["min_gpu_temp"] == 45
    assert summary["avg_gpu_temp"] == round((45 + 75 + 60) / 3, 1)

    assert summary["peak_cpu_rpm"] == 3200
    assert summary["peak_gpu_rpm"] == 3000


def test_tracker_handles_none_values_gracefully():
    tracker = SessionMetricsTracker()

    # Feed snapshot with None values
    tracker.update(TelemetrySnapshot(cpu_temp=None, gpu_temp=None, cpu_rpm=None, gpu_rpm=None, is_ac_power=None, timestamp=time.time()))
    summary = tracker.get_summary()

    assert summary["sample_count"] == 1
    assert summary["peak_cpu_temp"] is None
    assert summary["avg_cpu_temp"] is None
    assert summary["peak_gpu_temp"] is None
    assert summary["avg_gpu_temp"] is None
    assert summary["peak_cpu_rpm"] is None
    assert summary["high_temp_excursion_seconds"] == 0.0


def test_tracker_excursion_duration_and_failsafe_trips():
    tracker = SessionMetricsTracker(start_ts=1000.0)

    # Initial safe reading at t=1000
    tracker.update(TelemetrySnapshot(cpu_temp=70, gpu_temp=65, cpu_rpm=2000, gpu_rpm=2000, is_ac_power=True, timestamp=1000.0))

    # Excursion reading (CPU=92°C >= 90) at t=1002 (delta = 2s)
    tracker.update(TelemetrySnapshot(cpu_temp=92, gpu_temp=70, cpu_rpm=2500, gpu_rpm=2500, is_ac_power=True, timestamp=1002.0))
    # Excursion reading at t=1004 (delta = 2s)
    tracker.update(TelemetrySnapshot(cpu_temp=94, gpu_temp=72, cpu_rpm=2800, gpu_rpm=2800, is_ac_power=True, timestamp=1004.0))

    assert tracker.high_temp_excursion_seconds == 4.0

    # Suspended sleep spike (delta = 100s) -> should be clamped by MAX_SAMPLE_INTERVAL_GRACE_SEC (not added)
    tracker.update(TelemetrySnapshot(cpu_temp=91, gpu_temp=70, cpu_rpm=2500, gpu_rpm=2500, is_ac_power=True, timestamp=1104.0))
    assert tracker.high_temp_excursion_seconds == 4.0

    # Record fail-safe trip
    assert tracker.failsafe_trip_count == 0
    tracker.record_failsafe_trip()
    tracker.record_failsafe_trip()
    assert tracker.failsafe_trip_count == 2
    assert tracker.get_summary()["failsafe_trip_count"] == 2


def test_sustained_advisory_trigger_and_cooldown():
    tracker = SessionMetricsTracker(start_ts=1000.0)

    # 1. Below threshold -> No advisory
    tracker.update(TelemetrySnapshot(cpu_temp=80, gpu_temp=70, cpu_rpm=2000, gpu_rpm=2000, is_ac_power=True, timestamp=1000.0))
    assert not tracker.should_trigger_advisory("Balanced", now=1000.0)

    # 2. Excursion begins at t=1002 (CPU=92°C)
    tracker.update(TelemetrySnapshot(cpu_temp=92, gpu_temp=75, cpu_rpm=2500, gpu_rpm=2500, is_ac_power=True, timestamp=1002.0))
    # Only 10s elapsed -> No advisory (< 30s)
    assert not tracker.should_trigger_advisory("Balanced", now=1012.0)

    # 3. 32 seconds continuous excursion elapsed in Balanced mode -> Triggers advisory
    assert tracker.should_trigger_advisory("Balanced", now=1035.0)

    # 4. Immediate subsequent check -> Cooldown active (must wait 300s)
    assert not tracker.should_trigger_advisory("Balanced", now=1036.0)
    assert not tracker.should_trigger_advisory("Balanced", now=1200.0)

    # 5. In G_Mode or Performance -> Should NOT trigger advisory (user is already in high cooling profile)
    assert not tracker.should_trigger_advisory("G_Mode", now=1400.0)
    assert not tracker.should_trigger_advisory("Performance", now=1400.0)

    # 6. Past 300s cooldown in Quiet mode -> Triggers advisory
    assert tracker.should_trigger_advisory("Quiet", now=1400.0)


def test_appgui_tray_tooltip_displays_peaks_and_trips(qapp):
    orig_hotkey = HotKey.start
    HotKey.start = lambda self: None
    orig_watchdog = TCC_GUI._startWatchdog
    TCC_GUI._startWatchdog = lambda self: None

    try:
        awcc = MagicMock()
        awcc.GPUFanIdx = 0
        awcc.CPUFanIdx = 1
        awcc.Mode.Balanced = 1
        awcc.Mode.G_Mode = 4
        awcc.setMode.return_value = True

        with patch('GUI.AppGUI.DetectHardware'):
            window = TCC_GUI(awcc)
            window.toasterMessage = MagicMock()

            # Set starting mode
            window._modeSwitch.setChecked(ThermalMode.Balanced.value)

            # Telemetry tick 1: 75°C CPU, 65°C GPU
            snap1 = TelemetrySnapshot(cpu_temp=75, gpu_temp=65, cpu_rpm=2000, gpu_rpm=2100, is_ac_power=True, timestamp=100.0)
            window._onTelemetryReady(snap1)

            # Telemetry tick 2: Excursion to 92°C CPU, 78°C GPU
            snap2 = TelemetrySnapshot(cpu_temp=92, gpu_temp=78, cpu_rpm=3000, gpu_rpm=3100, is_ac_power=True, timestamp=102.0)
            window._onTelemetryReady(snap2)

            # Telemetry tick 3: Load drops to 60°C CPU, 55°C GPU
            snap3 = TelemetrySnapshot(cpu_temp=60, gpu_temp=55, cpu_rpm=1800, gpu_rpm=1900, is_ac_power=True, timestamp=104.0)
            window._onTelemetryReady(snap3)

            # Tray tooltip must reflect current 60°C/55°C but retain PEAKS (92°C CPU, 78°C GPU)
            tip = window.findChild(QtWidgets.QSystemTrayIcon).toolTip()
            assert "GPU: 55 °C (Peak: 78 °C)" in tip
            assert "CPU: 60 °C (Peak: 92 °C)" in tip
            assert "Mode: Balanced" in tip

            # Record a trip
            window._sessionTracker.record_failsafe_trip()
            window._onTelemetryReady(snap3)
            tip_tripped = window.findChild(QtWidgets.QSystemTrayIcon).toolTip()
            assert "(Trips: 1)" in tip_tripped

            window._destroy()
    finally:
        HotKey.start = orig_hotkey
        TCC_GUI._startWatchdog = orig_watchdog


def test_diagnostics_includes_session_metrics(tmp_path, monkeypatch):
    from pathlib import Path
    monkeypatch.setattr(Diagnostics, '_awccDump', lambda: {})
    monkeypatch.setattr(Diagnostics, '_wmi', lambda *a: {'Win32_ComputerSystem': [{'Model': 'Test G15'}]})

    tracker = SessionMetricsTracker(start_ts=2000.0)
    tracker.update(TelemetrySnapshot(cpu_temp=88, gpu_temp=74, cpu_rpm=2800, gpu_rpm=2700, is_ac_power=True, timestamp=2002.0))
    tracker.record_failsafe_trip()
    set_session_tracker(tracker)

    zip_path, _ = Diagnostics.build('TCC Test', '1.8.5')
    assert zip_path is not None
    assert zipfile.is_zipfile(zip_path)

    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            namelist = z.namelist()
            assert 'session_metrics.json' in namelist

            with z.open('session_metrics.json') as f:
                data = json.load(f)
                assert data['peak_cpu_temp'] == 88
                assert data['peak_gpu_temp'] == 74
                assert data['failsafe_trip_count'] == 1
                assert data['peak_cpu_rpm'] == 2800
    finally:
        Path(zip_path).unlink(missing_ok=True)
