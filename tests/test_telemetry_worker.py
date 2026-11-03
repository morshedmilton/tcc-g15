import pytest
from unittest.mock import MagicMock
from dataclasses import FrozenInstanceError
from PySide6 import QtCore, QtWidgets

from Backend.TelemetryTypes import TelemetrySnapshot
from GUI.TelemetryWorker import TelemetryWorker, sanitizeTemperature, queryAcPowerStatus

def test_telemetry_snapshot_immutability():
    """TelemetrySnapshot must be frozen and immutable across thread boundaries."""
    snap = TelemetrySnapshot(
        cpu_temp=65,
        gpu_temp=58,
        cpu_rpm=2200,
        gpu_rpm=2400,
        is_ac_power=True
    )
    assert snap.cpu_temp == 65
    assert snap.gpu_temp == 58
    assert snap.cpu_rpm == 2200
    assert snap.gpu_rpm == 2400
    assert snap.is_ac_power is True
    assert snap.timestamp > 0.0

    # Immutability check
    with pytest.raises(FrozenInstanceError):
        snap.cpu_temp = 90  # type: ignore

def test_sanitize_temperature_bounds():
    """Sanitizer preserves plausible hardware temperatures (0-125°C) and rejects glitches."""
    assert sanitizeTemperature(0) == 0
    assert sanitizeTemperature(55) == 55
    assert sanitizeTemperature(100) == 100
    assert sanitizeTemperature(125) == 125

    # Out of bounds & glitched readings must degrade to None
    assert sanitizeTemperature(-1) is None
    assert sanitizeTemperature(-40) is None
    assert sanitizeTemperature(126) is None
    assert sanitizeTemperature(255) is None
    assert sanitizeTemperature(None) is None
    assert sanitizeTemperature("corrupt") is None  # type: ignore

def test_telemetry_worker_polling_and_signal(qapp):
    """TelemetryWorker queries sensors and emits TelemetrySnapshot signal cleanly."""
    mock_awcc = MagicMock()
    mock_awcc.GPUFanIdx = 0
    mock_awcc.CPUFanIdx = 1
    mock_awcc.getFanRelatedTemp.side_effect = lambda idx: 52 if idx == 0 else 68
    mock_awcc.getFanRPM.side_effect = lambda idx: 2100 if idx == 0 else 2300

    mock_gpu_temp = MagicMock()
    mock_gpu_temp.read.return_value = 55  # Direct NVML reading

    worker = TelemetryWorker(awcc=mock_awcc, gpuTemp=mock_gpu_temp)
    received = []

    worker.telemetryReady.connect(lambda snap: received.append(snap))
    worker._running = True
    worker.pollOnce()

    assert len(received) == 1
    snap = received[0]
    assert isinstance(snap, TelemetrySnapshot)
    assert snap.gpu_temp == 55  # NVML preferred
    assert snap.cpu_temp == 68
    assert snap.gpu_rpm == 2100
    assert snap.cpu_rpm == 2300

def test_telemetry_worker_fallback_to_wmi_when_nvml_none(qapp):
    """When NVML is unavailable or returns None, worker falls back to Dell WMI sensor."""
    mock_awcc = MagicMock()
    mock_awcc.GPUFanIdx = 0
    mock_awcc.CPUFanIdx = 1
    mock_awcc.getFanRelatedTemp.side_effect = lambda idx: 59 if idx == 0 else 72
    mock_awcc.getFanRPM.return_value = 1800

    mock_gpu_temp = MagicMock()
    mock_gpu_temp.read.return_value = None  # NVML unavailable

    worker = TelemetryWorker(awcc=mock_awcc, gpuTemp=mock_gpu_temp)
    received = []
    worker.telemetryReady.connect(lambda snap: received.append(snap))
    worker._running = True
    worker.pollOnce()

    assert len(received) == 1
    snap = received[0]
    assert snap.gpu_temp == 59  # Fell back to Dell WMI sensor
    assert snap.cpu_temp == 72

def test_telemetry_worker_thread_lifecycle(qapp):
    """TelemetryWorker starts, runs in a secondary QThread, and stops cleanly."""
    mock_awcc = MagicMock()
    mock_awcc.GPUFanIdx = 0
    mock_awcc.CPUFanIdx = 1
    mock_awcc.getFanRelatedTemp.return_value = 50
    mock_awcc.getFanRPM.return_value = 2000

    mock_gpu = MagicMock()
    mock_gpu.read.return_value = 50

    thread = QtCore.QThread()
    worker = TelemetryWorker(awcc=mock_awcc, gpuTemp=mock_gpu, pollingIntervalMs=50)
    worker.moveToThread(thread)

    snapshots = []
    worker.telemetryReady.connect(lambda snap: snapshots.append(snap))

    thread.started.connect(worker.start)
    thread.start()

    # Process events to allow thread startup and initial poll
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(150, loop.quit)
    loop.exec()

    # Verify at least one snapshot was received from secondary thread
    assert len(snapshots) >= 1

    # Adjust interval dynamically
    worker.setInterval(100)
    assert worker._pollingIntervalMs == 100

    # Clean shutdown
    worker.stop()
    thread.quit()
    assert thread.wait(1000) is True

def test_telemetry_error_signal_on_exception(qapp):
    """TelemetryWorker emits telemetryError signal if an unexpected hardware query fails."""
    mock_awcc = MagicMock()
    mock_awcc.getFanRelatedTemp.side_effect = RuntimeError("Hardware bus fault")

    worker = TelemetryWorker(awcc=mock_awcc, gpuTemp=None)
    errors = []
    worker.telemetryError.connect(lambda err: errors.append(err))
    worker._running = True

    # Simulate forced exception during pollOnce by breaking internal state
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(worker, "_awcc", MagicMock(getFanRelatedTemp=MagicMock(side_effect=RuntimeError("Bus lock"))))
        mp.setattr(worker, "_gpuTemp", MagicMock(read=MagicMock(side_effect=RuntimeError("Bus lock"))))
        worker.pollOnce()

    assert len(errors) == 1
    assert "Bus lock" in errors[0]
