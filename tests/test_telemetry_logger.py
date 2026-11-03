import csv
import time
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

from Backend.TelemetryTypes import TelemetrySnapshot
from Backend.TelemetryLogger import TelemetryLogger
from GUI import Diagnostics

def test_telemetry_logger_header_and_row_format(tmp_path):
    """TelemetryLogger writes standard RFC 4180 CSV with header and structured rows."""
    logger = TelemetryLogger(logDir=tmp_path, enabled=True)
    assert logger.current_log_path is not None
    assert logger.current_log_path.exists()

    snap = TelemetrySnapshot(
        cpu_temp=62,
        gpu_temp=54,
        cpu_rpm=2100,
        gpu_rpm=2200,
        is_ac_power=True,
        timestamp=1700000000.0
    )
    ok = logger.log(snap, mode="Balanced")
    assert ok is True
    logger.close()

    # Read back CSV
    with open(logger.current_log_path, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))

    assert len(reader) == 2
    assert reader[0] == TelemetryLogger.CSV_HEADER
    row = reader[1]
    assert row[0] == "1700000000.00"
    assert "2023" in row[1] or "2024" in row[1] or "T" in row[1]
    assert row[2] == "62"
    assert row[3] == "54"
    assert row[4] == "2100"
    assert row[5] == "2200"
    assert row[6] == "Balanced"
    assert row[7] == "AC"

def test_telemetry_logger_disabled_toggle(tmp_path):
    """When disabled, TelemetryLogger skips file creation and logging calls return False."""
    logger = TelemetryLogger(logDir=tmp_path, enabled=False)
    assert logger.current_log_path is None

    snap = TelemetrySnapshot(cpu_temp=50, gpu_temp=45, cpu_rpm=2000, gpu_rpm=2000, is_ac_power=False)
    assert logger.log(snap, "Quiet") is False

    # Enable dynamically
    logger.set_enabled(True)
    assert logger.current_log_path is not None
    assert logger.log(snap, "Quiet") is True
    logger.close()

def test_telemetry_logger_bounded_size_guard(tmp_path, monkeypatch):
    """Logger enforces MAX_FILE_BYTES ceiling and ceases writing to prevent disk exhaustion."""
    logger = TelemetryLogger(logDir=tmp_path, enabled=True)
    monkeypatch.setattr(logger, "MAX_FILE_BYTES", 200)  # Very small 200-byte cap

    snap = TelemetrySnapshot(cpu_temp=70, gpu_temp=60, cpu_rpm=3000, gpu_rpm=3000, is_ac_power=True)
    # Write rows until cap is reached
    written = 0
    for _ in range(20):
        if logger.log(snap, "Performance"):
            written += 1

    assert written > 0
    # Must stop accepting writes once bytesWritten >= 200
    assert logger._bytesWritten >= 200
    assert logger.log(snap, "Performance") is False
    logger.close()

def test_telemetry_logger_prune_old_sessions(tmp_path, monkeypatch):
    """Logger prunes sessions beyond MAX_RETAINED_SESSIONS, keeping only the newest."""
    # Create 7 mock session files
    for i in range(7):
        p = tmp_path / f"session_20261104_0{i}0000.csv"
        p.write_text("header\n", encoding="utf-8")
        time.sleep(0.01)

    assert len(list(tmp_path.glob("session_*.csv"))) == 7

    # Initialize logger with max 5 sessions
    logger = TelemetryLogger(logDir=tmp_path, enabled=True)
    logger.close()

    remaining = list(tmp_path.glob("session_*.csv"))
    # Should be capped at MAX_RETAINED_SESSIONS (5)
    assert len(remaining) <= 5

def test_telemetry_logger_get_recent_logs(tmp_path):
    """get_recent_logs returns session files sorted newest first."""
    p1 = tmp_path / "session_20261104_010000.csv"
    p1.write_text("1", encoding="utf-8")
    time.sleep(0.02)
    p2 = tmp_path / "session_20261104_020000.csv"
    p2.write_text("2", encoding="utf-8")

    recent = TelemetryLogger.get_recent_logs(tmp_path)
    assert len(recent) == 2
    assert recent[0] == p2  # Newest first
    assert recent[1] == p1

def test_diagnostics_bundle_includes_telemetry(tmp_path, monkeypatch):
    """Diagnostics.build includes telemetry.csv in bugreport zip if available."""
    sample_csv = tmp_path / "session_sample.csv"
    sample_csv.write_text("timestamp_unix,cpu_temp\n1000,65\n", encoding="utf-8")

    monkeypatch.setattr(TelemetryLogger, "get_recent_logs", classmethod(lambda cls, *args: [sample_csv]))
    monkeypatch.setattr(Diagnostics, "_wmi", lambda *a: {"test": "data"})
    monkeypatch.setattr(Diagnostics, "_awccDump", lambda: {"fans": []})

    zip_path, url = Diagnostics.build("TCC Test", "1.8.4")
    assert zip_path is not None
    assert Path(zip_path).exists()

    # Verify telemetry.csv is present in zip
    with zipfile.ZipFile(zip_path, "r") as z:
        names = z.namelist()
        assert "telemetry.csv" in names
        assert "system.json" in names
        assert "wmi.json" in names
        assert "awcc.json" in names
        content = z.read("telemetry.csv").decode("utf-8")
        assert "1000,65" in content

    # Clean up test zip
    Path(zip_path).unlink(missing_ok=True)
