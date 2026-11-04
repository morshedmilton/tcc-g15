# Thermal Control Center (TCC-G15) — Release v1.8.5

**Release Tag:** `v1.8.5`  
**Date:** 2026-11-04  
**Commit / Target:** `main`  
**License:** GPL-3.0  
**Repository:** https://github.com/morshedmilton/tcc-g15  

---

## What's New in v1.8.5

Release v1.8.5 delivers advanced in-memory session thermal analytics, persistent system tray peak indicators, and proactive thermal overload advisories, empowering users to monitor thermal saturation dynamics during demanding gaming and rendering workloads.

### 1. In-Memory Session Thermal Analytics Engine (`OPP-007` / ADR-005)
- **`SessionMetricsTracker` Engine:** Continuously aggregates running statistics over the lifecycle of an application session with $O(1)$ computational efficiency and zero disk I/O latency.
- **Tracked Analytics:**
  - **Peak Temperatures:** Records maximum observed CPU and GPU temperatures.
  - **Minimum & Average Temperatures:** Computes arithmetic running averages and records lowest temperatures.
  - **Fan RPM Extremes:** Captures peak CPU and GPU fan speeds achieved.
  - **Cumulative Excursion Duration:** Tracks total seconds spent in high-temperature excursion state (CPU >= 90°C or GPU >= 82°C) with standby/sleep clamping.
  - **Fail-Safe Trip Tracking:** Records total emergency fail-safe trips triggered during the session.

### 2. System Tray Tooltip Peak Display
- Glancing at the system tray tooltip now reveals both instantaneous and session peak values:
  ```text
  GPU: 60 °C (Peak: 78 °C)    2400 RPM
  CPU: 72 °C (Peak: 93 °C)    2700 RPM
  Mode: Balanced (Trips: 0)
  ```
- Solves the longstanding problem where minimizing a game caused temperatures to instantly drop to idle before the user could read the peak thermal stress reached under load.

### 3. Proactive Sustained Saturation Advisory
- If temperatures sustain near trip thresholds (CPU >= 90°C or GPU >= 82°C) for 30 consecutive seconds in lower cooling profiles (`Quiet` or `Balanced`), TCC-G15 issues a single informative toast notification:
  > *"Thermal Advisory: Sustained high temperatures detected. Consider a higher cooling profile."*
- Built-in 300-second (5-minute) cooldown prevents notification spam while keeping hardware safe from prolonged thermal throttling.

### 4. Diagnostics Bug Report Integration
- `Diagnostics.build()` now automatically embeds `session_metrics.json` directly into the bug report zip, providing instant summary metrics without requiring manual parsing of time-series CSV logs.

---

## Cryptographic Artifact Hashes

| Distribution | File Name | Size | SHA-256 Checksum |
|---|---|---|---|
| **Windows Installer** | `tcc-g15-installer-1.8.5.exe` | 45,143,969 bytes | `13D3262E91C36E9C29126003ABBB48D5F47B9B5E9EA9FAA50947B3EE7799BC07` |
| **Portable Zip** | `tcc-g15-portable-1.8.5.zip` | 59,487,708 bytes | `38B4FCB37C7113786B00A87F282F82A42626CD08158A100260296C7425E960D4` |
| **CycloneDX SBOM** | `tcc-g15-sbom.json` | 6,136 bytes | `0F2F1DB389E9955009A1DA64CB22C48EBE762B13F9F6B01AD2A60766D5C470DF` |

---

## Verification & Test Results
- **Pytest Suite:** 42 of 42 unit tests passing (`42 passed in 6.27s`).
- **Safety Invariant Verification:** Verified INV-1 (Hard emergency trip), INV-2 (Bounded polling timeout), and INV-6 (Clean COM apartment isolation).
- **Code Quality:** Ruff linter passed with 0 errors across `src/`, `tests/`, and `tools/`.
