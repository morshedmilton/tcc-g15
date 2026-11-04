# TCC-G15 Engineering Report — Cycle 005

**Cycle:** 005  
**Target Release:** v1.8.5 (Observability, Session Thermal Analytics & Proactive Advisories)  
**Status:** COMPLETED & SHIPPED  
**Cycle Dates:** 2026-11-04  
**Author:** Multi-disciplinary Autonomous Engineering Organization  
**Release Tag:** `v1.8.5` (https://github.com/morshedmilton/tcc-g15/releases/tag/v1.8.5)

---

## 1. Executive Summary

Cycle 005 implements the thermal observability and proactive early warning requirements specified in `OPP-007` (ADR-005):
1. **Session Thermal Analytics Engine (`OPP-007` / ADR-005):** Created `SessionMetricsTracker` recording peak CPU/GPU temperatures, minimum temperatures, arithmetic averages, peak fan RPMs, cumulative high-temperature excursion duration, and fail-safe trip counts with O(1) in-memory computation.
2. **System Tray Tooltip Peak Display:** Enhanced the system tray tooltip to display session peak temperatures and trip counts alongside instantaneous values (`GPU: 55 °C (Peak: 78 °C) ... Mode: Balanced (Trips: 0)`), giving users persistent visibility into peak thermal load after gaming or rendering.
3. **Proactive Sustained Saturation Advisory:** Added intelligent advisory toasts when CPU >= 90°C or GPU >= 82°C sustains for >= 30 continuous seconds in `Quiet` or `Balanced` modes, with a strict 300-second (5-minute) cooldown to avoid user notification fatigue.
4. **Diagnostics Bug Report Integration:** `Diagnostics.build()` automatically embeds `session_metrics.json` into the root of `bugreport-<stamp>.zip`, giving maintainers immediate insight into session thermal stress.
5. **Safety Invariants Preservation (INV-1 to INV-6):** Hard emergency trip logic (CPU >= 100°C) and soft fail-safe protection remain completely unbypassable; all new tracking runs in memory with zero file I/O latency.

---

## 2. Evidence & Test Results

### 2.1 Automated Pytest Suite
- **Command:** `.venv\Scripts\python.exe -m pytest tests/ -v`
- **Result:** **42 passed in 6.27s** (100% pass rate)
- New tests in `tests/test_session_metrics.py`:
  - `test_tracker_peaks_and_averages` (PASSED)
  - `test_tracker_handles_none_values_gracefully` (PASSED)
  - `test_tracker_excursion_duration_and_failsafe_trips` (PASSED)
  - `test_sustained_advisory_trigger_and_cooldown` (PASSED)
  - `test_appgui_tray_tooltip_displays_peaks_and_trips` (PASSED)
  - `test_diagnostics_includes_session_metrics` (PASSED)

### 2.2 Environment & Linter Verification
- `tools/check_env.py`: **ALL CHECKS PASSED**
- `ruff check src/ tests/ tools/`: **All checks passed!**

---

## 3. Cryptographic Release Artifacts (v1.8.5)

| Distribution | File Name | Size | SHA-256 Checksum |
|---|---|---|---|
| **Windows Installer** | `tcc-g15-installer-1.8.5.exe` | 45,143,969 bytes | `13D3262E91C36E9C29126003ABBB48D5F47B9B5E9EA9FAA50947B3EE7799BC07` |
| **Portable Zip** | `tcc-g15-portable-1.8.5.zip` | 59,487,708 bytes | `38B4FCB37C7113786B00A87F282F82A42626CD08158A100260296C7425E960D4` |
| **CycloneDX SBOM** | `tcc-g15-sbom.json` | 6,136 bytes | `0F2F1DB389E9955009A1DA64CB22C48EBE762B13F9F6B01AD2A60766D5C470DF` |

---

## 4. Gate Sign-Off Matrix

- **G0 (Delta Reconnaissance):** PASSED (Signed by Orchestrator A, Reviewer L)
- **G1 (Research & Delta Intel):** PASSED (Signed by Orchestrator A, Reviewer L)
- **G2 (Forensic Audit):** PASSED (Signed by Safety E, Security I, Reviewer L)
- **G3 (Prioritization & Scope):** PASSED (Signed by Orchestrator A, Reviewer L)
- **G4 (Requirements & Plan):** PASSED (Signed by Orchestrator A, QA J)
- **G5 (Design & ADRs):** PASSED (Signed by Architect B, Safety E, Reviewer L; ADR-005 accepted)
- **G6 (Implementation):** PASSED (Signed by QA J, Reviewer L)
- **G7 (Quality Verification):** PASSED (42/42 tests passing, ruff & check_env 100% green)
- **G8 (Packaging & Release Readiness):** PASSED (Signed by DevOps K, Reviewer L; Binaries & SBOM verified)
- **G9 (Deployment & Release Monitoring):** PASSED (Signed by Orchestrator A; Release v1.8.5 published & verified)
