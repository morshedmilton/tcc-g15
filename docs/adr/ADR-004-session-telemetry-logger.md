# ADR-004: Bounded Session Telemetry Logger & Diagnostics Integration

**Status:** Accepted  
**Date:** 2026-11-04  
**Author:** Multi-disciplinary Autonomous Engineering Organization  
**Supersedes / Relates to:** PRD Cycle 004 (`OPP-006`), ADR-003  

---

## 1. Context & Problem Statement

Users troubleshooting thermal throttling, benchmarking cooling profiles under gaming loads, or reporting firmware bugs lacked persistent telemetry history. The existing "Create bug report" diagnostic bundle captured static WMI classes and the latest text log, but lacked time-series telemetry showing temperatures and fan RPM dynamics preceding crashes or throttling events.

Unrestricted disk logging, however, poses disk exhaustion risks if an application runs continuously for days or weeks.

## 2. Decision Drivers

- **Observability:** Capture granular time-series thermal and fan data in a standard, easily analyzable format (RFC 4180 CSV).
- **Strict Bounded Disk Usage:** Never allow logs to consume unbounded disk space.
- **Fail-Safe Non-Interference (INV-1):** Disk write failures (e.g. out of space, write lock) must never throw uncaught exceptions into the GUI or interrupt fail-safe trips.
- **Privacy & Redaction:** No user identities, MAC addresses, or serial numbers may be recorded in telemetry logs.
- **Diagnostic Bundling:** Automatically attach the latest session telemetry CSV into the bug report zip created by `Diagnostics.build()`.

## 3. Considered Options

1. **Option A: SQLite Database.**
   - *Rejected:* Heavyweight dependency for simple sequential time-series; difficult for users to inspect with Excel, Sheets, or text editors.
2. **Option B: Unbounded text log file.**
   - *Rejected:* Violates disk footprint hygiene; risks disk saturation on long-running systems.
3. **Option C: Bounded CSV session logging with automatic session retention & file size ceiling.**
   - *Accepted:* Lightweight, universally compatible (RFC 4180 CSV). Enforces strict limits: max 10MB per session file, max 5 retained sessions.

## 4. Architecture Design

### File Location & Naming
- Target directory: `%LOCALAPPDATA%\tcc-g15\telemetry\` (fallback: `%TEMP%\tcc-g15\telemetry\`).
- File pattern: `session_YYYYMMDD_HHMMSS.csv`.

### CSV Schema
```csv
timestamp_unix,iso_datetime,cpu_temp_c,gpu_temp_c,cpu_fan_rpm,gpu_fan_rpm,mode,ac_power
```

### Retention & Bounds
- **Maximum File Size:** 10 MB per session (~160,000 readings = >88 continuous hours at 2s poll).
- **Session Retention Guard:** On startup, prune any session CSVs exceeding the 5 most recent files.
- **Opt-in / Persistent Toggle:** Configured via `app/telemetry_logging` in `QSettings`, toggled via Tray Context Menu.
- **Diagnostics Integration:** `Diagnostics.build()` automatically discovers the latest session CSV and includes it as `telemetry.csv` in the generated bug report zip.

## 5. Consequences & Verification

- **Positive:** Users can inspect thermal trends and export CSVs for graphing; bug reports include granular hardware behavior leading up to reported issues.
- **Negative:** Minor disk I/O (~30 bytes/sec when enabled), mitigated by buffered file operations.
- **Verification:** Unit tests in `tests/test_telemetry_logger.py` covering header creation, row formatting, rotation, size cap, and exception resilience.
