# ADR-003: Decoupled Background Telemetry Worker Thread

**Status:** Accepted  
**Date:** 2026-11-04  
**Author:** Multi-disciplinary Autonomous Engineering Organization  
**Supersedes / Relates to:** PRD Cycle 003 (`OPP-001`, `OPP-005`)  

---

## 1. Context & Problem Statement

In previous versions (v1.8.0 through v1.8.2), telemetry queries—consisting of Dell ACPI WMI calls for CPU/GPU temperatures and fan RPMs, NVIDIA NVML driver queries, and Win32 AC power queries—executed synchronously directly inside the Qt GUI Main Thread (`QPeriodic` timer in `TCC_GUI`).

Each synchronous WMI COM call dispatches `Thermal_Information` to `root\WMI` on Windows, taking between 15ms and 80ms under normal conditions, and up to 300ms during intense gaming or CPU-heavy workloads. This caused periodic micro-stutters in window dragging, button hovering, and UI animations.

## 2. Decision Drivers

- **Zero UI Latency:** The Qt GUI Main Thread must never be blocked by hardware I/O or COM bus contention.
- **COM Apartment Threading:** Windows COM restricts multi-threaded access; COM objects must be instantiated within the thread that invokes them (`pythoncom.CoInitialize()`).
- **Safety Invariant Preservation:**
  - INV-1 (Hard fail-safe): Must immediately trip if critical temperatures (100°C CPU / 90°C GPU) are reported.
  - INV-2 (Fail-safe timeout bound): If the worker thread hangs or crashes, the GUI thread must detect sensor timeout and trip safely.
  - INV-4 (Watchdog heartbeat): Heartbeat file must continue to be touched predictably.
- **Graceful Lifecycle Management:** The background thread must terminate cleanly on application exit without leaving orphaned threads or triggering Qt C++ teardown crashes.

## 3. Considered Options

1. **Option A: Keep polling on Qt Main Thread with reduced frequency (e.g. 5s).**
   - *Rejected:* Does not eliminate the micro-stutter when it occurs; makes fail-safe response slower.
2. **Option B: Subclass `QtCore.QThread` and override `run()`.**
   - *Rejected:* Qt official best practice discourages subclassing `QThread` for worker objects; `QObject.moveToThread()` provides clean signal/slot semantics and event loop integration.
3. **Option C: `TelemetryWorker(QObject)` with `moveToThread(QThread)` emitting `TelemetrySnapshot`.**
   - *Accepted:* Standard Qt worker pattern. Worker runs its own polling timer in the secondary thread, performs COM initialization via `pythoncom`, queries NVML and WMI, constructs an immutable `TelemetrySnapshot` DTO, and emits it via queued signal to the main thread.

## 4. Architecture Design

```
                      +-----------------------------+
                      |       Qt GUI Thread         |
                      |          (TCC_GUI)          |
                      +--------------+--------------+
                                     ^
                                     |  Signal: telemetryReady(TelemetrySnapshot)
                                     |  (QueuedConnection across thread boundary)
                      +--------------+--------------+
                      |      TelemetryWorker        |
                      |   (runs inside QThread)     |
                      +--------------+--------------+
                                     |
               +---------------------+---------------------+
               |                                           |
               v                                           v
      +-----------------+                         +-----------------+
      |  Dell ACPI WMI  |                         |   NVIDIA NVML   |
      |  (root\WMI COM) |                         | (nvml.dll C API)|
      +-----------------+                         +-----------------+
```

### Safety & Timeout Fallback
If the worker thread fails to emit a `TelemetrySnapshot` for longer than `FAILSAFE_UNKNOWN_GRACE_SEC` (60 seconds), the GUI thread initiates the safe fail-safe trip to G-Mode with maximum fan cooling per Invariant INV-2.

## 5. Consequences & Verification

- **Positive:** UI thread latency drops to < 1 ms per tick. Window movement, animations, and interactions remain perfectly smooth even under 100% CPU load.
- **Verification:** Unit tests with mocked HAL and signal verification in `tests/test_telemetry_worker.py`. 100% clean teardown verified in CI.
