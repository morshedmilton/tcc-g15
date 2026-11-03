# Thermal Control Center (TCC-G15) — Release v1.8.4

**Release Tag:** `v1.8.4`  
**Date:** 2026-11-04  
**Commit / Target:** `main`  
**License:** GPL-3.0  
**Repository:** https://github.com/morshedmilton/tcc-g15  

---

## What's New in v1.8.4

Release v1.8.4 introduces full session telemetry logging and deeper diagnostics observability, empowering users and maintainers to correlate fan acoustics, power state transitions, and thermal throttling behavior over time.

### 1. Bounded Session Telemetry Logging (`OPP-006` / ADR-004)
- **Standard RFC 4180 CSV Export:** Telemetry snapshots are recorded to `%LOCALAPPDATA%\tcc-g15\telemetry\session_<YYYYMMDD_HHMMSS>.csv`.
- **Recorded Metrics:** Unix epoch timestamp, ISO-8601 local timestamp, CPU temperature (°C), GPU temperature (°C), CPU fan RPM, GPU fan RPM, active thermal mode (`Custom`, `Balanced`, `Performance`, `Quiet`, `G_Mode`), and AC line power status (`True`/`False`).
- **Non-Interfering Sandboxing:** Logging runs without locking or impeding the high-priority hardware fail-safe routines (INV-1 / INV-2). Any filesystem errors or permissions issues are safely caught.

### 2. Strict Bounded Retention & Size Guard
- **Size Capping:** Individual session CSV files are strictly capped at 10 MB (~88 hours of continuous 2-second polling). Once the limit is reached, logging cleanly suspends for the session.
- **Automatic Rotation Pruning:** Automatically prunes older sessions, retaining a maximum of 5 recent log files to guarantee zero unbounded disk accumulation on user systems.

### 3. Tray Context Menu Controls & Persistence
- **Toggle Logging:** Easily toggle telemetry logging on or off directly via the tray icon context menu (*"Session telemetry logging"*).
- **One-Click Log Access:** Click *"Open logs directory"* from the tray menu to immediately navigate to the telemetry logs folder in Windows Explorer.
- **Preference Persistence:** Logging preferences are saved under `app/telemetry_logging` in `QSettings`.

### 4. Diagnostics Bug Report Integration
- The built-in **"Create bug report"** feature now automatically includes the latest session `telemetry.csv` inside `bugreport-<stamp>.zip`. This provides maintainers with second-by-second thermal dynamics preceding any reported system anomaly.

---

## Cryptographic Artifact Hashes

| Distribution | File Name | Size | SHA-256 Checksum |
|---|---|---|---|
| **Windows Installer** | `tcc-g15-installer-1.8.4.exe` | 45,146,773 bytes (43.1 MB) | `3F39A1ACA1D40EFBEEFECD0E368572C95A38F6187B1171C4E8E995344F1868DF` |
| **Portable Zip** | `tcc-g15-portable-1.8.4.zip` | 59,484,638 bytes (56.7 MB) | `AF3C53892CE191946C61C9E86018158A2389F05A96DBC0FD7BEBC8D0F26314F4` |
| **CycloneDX SBOM** | `tcc-g15-sbom.json` | 6,136 bytes (6.0 KB) | `637D333A0B8A98AD5386EE8670247A6D0A7DA9D1EB2AA81B724207B880096F61` |

---

## Verification & Test Results
- **Pytest Suite:** 36 of 36 unit tests passing (`36 passed in 4.76s`).
- **Safety Invariant Verification:** Verified INV-1 (Hard emergency trip), INV-2 (Bounded polling timeout), and INV-6 (Clean COM apartment teardown).
- **Code Quality:** Ruff linter passed with 0 errors across `src/`, `tests/`, and `tools/`.
