# TCC-G15 Product Requirements Document (PRD) — Cycle 005

**Cycle:** 005  
**Target Release:** v1.8.5 (Observability, Session Thermal Analytics & Proactive Advisories)  
**Status:** Approved for Implementation  
**Author:** Orchestrator Role A  
**QA Lead:** QA Role J  
**Safety Lead:** Safety Role E  

---

## 1. Requirements Specification

### `REQ-0501`: Session Thermal Metrics Engine (`OPP-007`)
- **Problem:** TCC-G15 tracks instantaneous temperature, but provides no session-level aggregation of peak thermal stress, fan speeds, or thermal excursion durations.
- **Requirement:**
  1. Create `src/Backend/SessionMetricsTracker.py`.
  2. Maintain running session statistics:
     - `peak_cpu_temp`, `peak_gpu_temp` (integers)
     - `min_cpu_temp`, `min_gpu_temp` (integers)
     - `avg_cpu_temp`, `avg_gpu_temp` (floats)
     - `peak_cpu_rpm`, `peak_gpu_rpm` (integers)
     - `high_temp_excursion_seconds` (float, seconds with CPU >= 90°C or GPU >= 82°C)
     - `failsafe_trip_count` (integer)
     - `session_uptime_seconds` (float)
  3. Provide `get_summary()` returning a JSON-serializable dictionary.
  4. Ensure all arithmetic handles `None` values gracefully without exceptions.

### `REQ-0502`: System Tray Tooltip Peak Thermal Display
- **Problem:** Users glancing at the system tray after a gaming or rendering session see dropped idle temperatures instead of the peak thermal stress reached under load.
- **Requirement:**
  Update tray tooltip format in `AppGUI.py` to:
  ```text
  GPU: {gpuTemp or '--'} °C (Peak: {peakGpu or '--'} °C)    {gpuRPM or '--'} RPM
  CPU: {cpuTemp or '--'} °C (Peak: {peakCpu or '--'} °C)    {cpuRPM or '--'} RPM
  Mode: {mode} (Trips: {failsafe_trips})
  ```

### `REQ-0503`: Proactive Sustained Saturation Advisory
- **Problem:** When running in low-noise profiles (`Quiet` or `Balanced`), sustained operations near trip limits (CPU 90°C–94°C or GPU 82°C–84°C) cause prolonged thermal throttling before an emergency trip occurs.
- **Requirement:**
  If CPU >= 90°C or GPU >= 82°C persists continuously for >= 30 seconds while in `Quiet` or `Balanced` mode, trigger a single informative toaster message:
  `["Thermal Advisory", "Sustained high temperatures detected. Consider a higher cooling profile.", "Thermal Safeguard"]`
  with a strict 300-second (5-minute) cooldown between advisories.

### `REQ-0504`: Diagnostics Bug Report Session Metrics Summary
- **Problem:** Bug report zips require manual parsing of entire CSV files to determine session peak stress.
- **Requirement:**
  `Diagnostics.build()` must query `SessionMetricsTracker.get_summary()` (via `AppGUI` or singleton/module) and write `session_metrics.json` into the root of the bug report zip.

---

## 2. Traceability Matrix

| Requirement | Opportunity ID | Primary File(s) | Verification Test |
|---|---|---|---|
| `REQ-0501` | `OPP-007` | `src/Backend/SessionMetricsTracker.py` | `tests/test_session_metrics.py::test_tracker_peaks_and_averages` |
| `REQ-0502` | `OPP-007` | `src/GUI/AppGUI.py` | `tests/test_session_metrics.py::test_tray_tooltip_includes_peaks` |
| `REQ-0503` | `OPP-007` | `src/GUI/AppGUI.py` | `tests/test_session_metrics.py::test_sustained_advisory_trigger_and_cooldown` |
| `REQ-0504` | `OPP-007` | `src/GUI/Diagnostics.py` | `tests/test_session_metrics.py::test_diagnostics_includes_session_metrics` |

---

## 3. Work Breakdown Structure (WBS)
- `TASK-501`: Create feature branch `cycle-005/thermal-analytics-advisory` (DONE).
- `TASK-502`: Implement `src/Backend/SessionMetricsTracker.py`.
- `TASK-503`: Integrate `SessionMetricsTracker` into `AppGUI.py` telemetry callback & tray tooltip.
- `TASK-504`: Implement proactive sustained saturation advisory with cooldown in `AppGUI.py`.
- `TASK-505`: Integrate `session_metrics.json` into `src/GUI/Diagnostics.py`.
- `TASK-506`: Write automated test suite in `tests/test_session_metrics.py`.
- `TASK-507`: Run full regression tests (`pytest`, `check_env.py`, `ruff check`).
- `TASK-508`: Update documentation (`CHANGELOG.md`, `CYCLE-005.md`, `RELEASE_NOTES_1.8.5.md`).
- `TASK-509`: Build executables, generate SBOM, build installer, compute hashes.
- `TASK-510`: Commit, push branch, open PR #5, verify CI, squash-merge to `main`, publish release `v1.8.5`.
