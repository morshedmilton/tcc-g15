# TCC-G15 Forensic Code, Safety & Security Audit

**Audit Date:** 2026-11-04  
**Auditors:** Safety Engineer E, Security Role I, Reviewer L (hats)  
**Target:** Git HEAD `6e7ad43`  

---

## 1. Safety Invariants Compliance Audit

| Invariant | Description | Code Location | Status | Findings & Remediation |
|---|---|---|---|---|
| **INV-1** | Hard emergency path forces maximum cooling (`G_Mode`) regardless of user soft fail-safe toggle | `src/GUI/AppGUI.py:665-674` | **PASS (Code) / GAP (Test)** | Logic in code correctly bypasses `self._failsafeOn` for `hardTrip`. **Defect DEF-003 (P0):** No automated unit test exists to prevent regression. Fix: Add mock trip test in `tests/test_safety_and_failsafe.py`. |
| **INV-2** | Invalid/implausible sensor data never lowers cooling | `src/GUI/AppGUI.py:847-849` | **PASS** | `_saneTemp` filters < 5°C and > 120°C. Verified by `test_temperature_sanity_filter`. |
| **INV-3** | Return to firmware-safe mode (Balanced) on crash/kill/hang within bound (12s) | `src/tcc-watchdog.py:46-48` | **PASS** | Heartbeat age checked every 2s. If stale > 12s, applies `ThermalMode.Balanced`. Verified by `tools/watchdog_test.ps1`. |
| **INV-4** | Fan offsets clamped strictly to verified range (0–100%) | `src/Backend/AWCCWmiWrapper.py:82`, `src/GUI/AppGUI.py:366` | **PASS** | `SetAddonSpeedPercent` asserts `0 <= speed <= 100`. Verified by `test_offs_slider_limits_0_to_100`. |
| **INV-5** | Unsupported models refuse execution unless explicit override set | `src/GUI/AppGUI.py:932-938`, `src/Backend/DetectHardware.py:34-41` | **DEFECT** | **Defect DEF-002 (P0):** `G16 7630` and `m15 R7` are documented as compatible in README but omitted from `SUPPORTED_MODELS`. Fix: Add to whitelist and verify with unit test. |
| **INV-6** | No change reduces cooling below stock firmware floor | Dell EC Firmware + `AWCCWmiWrapper.py` | **PASS** | WMI method `SetAddonSpeedPercent` only accepts positive offsets on top of EC base curve. Negative fan speeds are physically impossible. |

---

## 2. Security & Supply Chain Audit

1. **UAC Elevation:**
   - Manifest requires `requireAdministrator` to access `root\WMI`. This is unavoidable and standard for low-level ACPI driver access on Windows.
2. **Diagnostics Redaction:**
   - `src/GUI/Diagnostics.py` strips user names, Windows user profile paths, and IP addresses before creating the issue bundle zip. Verified clean.
3. **Dependency Supply Chain (DEF-005 / P1):**
   - `requirements.txt` currently uses `>=` lower bounds (`PySide6>=6.9.1`, `nvidia-ml-py>=12.535.108`).
   - Missing version pinning and lockfile.
   - Mixes test tool `pytest` into production runtime requirements.
   - **Remediation:** Pin exact known-good versions in `requirements.txt` and move `pytest` to `requirements-dev.txt`.
4. **Git Hygiene (DEF-004 / P1):**
   - 44 temporary runtime logs (`docs/baseline/*.log`), pid files, and status files are tracked in git.
   - **Remediation:** Remove from git tracking via `git rm --cached` and expand `.gitignore`.

---

## 3. CI / CD & Verification Audit

1. **CI Branch Trigger Defect (DEF-001 / P0):**
   - File `.github/workflows/ci.yml:4-7` specifies `branches: [ "master", "g15-5530" ]`.
   - The repository's primary and default branch is `main`.
   - Consequently, GitHub Actions has never executed on `main` or on pull requests targeting `main`.
   - **Remediation:** Change branches to `[ "main" ]` in `.github/workflows/ci.yml`.

---

## 4. Defect Register Summary

- **`DEF-001` (P0 - Critical):** CI workflow trigger mismatch (`main` branch missing).
- **`DEF-002` (P0 - Critical):** Hardware whitelist missing `G16 7630` and `m15 R7`.
- **`DEF-003` (P0 - Critical):** Missing automated unit test for INV-1 hard fail-safe trip.
- **`DEF-004` (P1 - High):** Tracked debug/log files in repository index.
- **`DEF-005` (P1 - High):** Unpinned dependencies and mixed runtime/dev requirements.
