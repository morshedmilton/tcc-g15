# TCC-G15 Engineering Report — Cycle 002

**Cycle:** 002  
**Target Release:** v1.8.2 (Reliability, Watchdog Sleep Resilience & SBOM)  
**Status:** COMPLETED & SHIPPED  
**Cycle Dates:** 2026-11-04  
**Author:** Multi-disciplinary Autonomous Engineering Organization  
**Release Tag:** `v1.8.2` (https://github.com/morshedmilton/tcc-g15/releases/tag/v1.8.2)

---

## 1. Executive Summary

Cycle 002 focused on system reliability, continuous hardware protection across operating system power events (sleep/standby), and software supply chain compliance:
1. **Watchdog Sleep & Standby Resilience (`OPP-002` / ADR-002):** Resolved the critical issue where Windows lid close or modern standby caused the watchdog to falsely detect a stale heartbeat, trigger Balanced mode, and exit—leaving the system unprotected after resume. Monotonic loop timing now recognizes suspend events and grants a full grace window.
2. **Watchdog Auto-Resurrection in GUI (`OPP-002`):** Implemented continuous process health verification; if the watchdog process ever terminates, the GUI automatically restarts it.
3. **Thermal Mode Apply Retry (`OPP-003`):** Hardened mode switching against transient WMI communication contention.
4. **CycloneDX SBOM (`OPP-004`):** Integrated automated generation of `tcc-g15-sbom.json` into the build and GitHub Actions CI pipelines.

---

## 2. Evidence & Test Results

### 2.1 Automated Pytest Suite
- **Command:** `.venv\Scripts\pytest.exe tests/ -v`
- **Result:** **24 passed in 4.76s** (100% pass rate)
- New tests:
  - `tests/test_whitelist_and_power.py::test_watchdog_resurrection` (PASSED)
  - `tests/test_wmi_wrapper.py::test_thermal_mode_apply_retry` (PASSED)

### 2.2 Environment & Linter Verification
- `tools/check_env.py`: **ALL CHECKS PASSED**
- `ruff check src/ tests/ tools/`: **All checks passed!**
- GitHub Actions CI Run [#41699805035](https://github.com/morshedmilton/tcc-g15/actions/runs/41699805035): **100% Green** across build, tests, PyInstaller packaging, and SBOM generation.

---

## 3. Cryptographic Release Artifacts (v1.8.2)

| Distribution | File Name | Size | SHA-256 Checksum |
|---|---|---|---|
| **Windows Installer** | `tcc-g15-installer-1.8.2.exe` | 45,130,627 bytes (43.0 MB) | `3D69442EAE133329F9473F4BFA4222BD70D9C171765BD9591B7FD3B26911F22D` |
| **Portable Zip** | `tcc-g15-portable-1.8.2.zip` | 68,605,627 bytes (65.4 MB) | `6BA122BDF6FD4E038D589A771A024DED39FC3E08B209B055B06535A3B10955BF` |
| **CycloneDX SBOM** | `tcc-g15-sbom.json` | 6,136 bytes (6.0 KB) | `CD594333E572ACC79BD4D5BD172439D18B38B5701F16DB425FD62744D79E47A6` |

---

## 4. Gate Sign-Off Matrix

- **G0 (Delta Reconnaissance):** PASSED (Signed by Orchestrator A, Reviewer L)
- **G1 (Research):** PASSED (Signed by Orchestrator A, Reviewer L)
- **G2 (Forensic Audit):** PASSED (Signed by Safety E, Security I, Reviewer L)
- **G3 (Prioritization & Scope):** PASSED (Signed by Orchestrator A, Reviewer L)
- **G4 (Requirements & Plan):** PASSED (Signed by Orchestrator A, QA J)
- **G5 (Design & ADRs):** PASSED (Signed by Architect B, Safety E, Reviewer L; ADR-002 accepted)
- **G6 (Implementation):** PASSED (Signed by QA J, Reviewer L)
- **G7 (Multi-level Verification):** PASSED (Signed by QA J, Safety E)
- **G8 (Release Engineering & Packaging):** PASSED (Signed by DevOps K, Reviewer L; PR #2 merged, v1.8.2 published)
- **G9 (Cycle Evaluation):** PASSED (Signed by Orchestrator A; Cycle 002 goals 100% achieved)

---

## 5. Next Cycle (Cycle 003) Preview
- `OPP-001` (Performance/Responsiveness): Decouple synchronous WMI / NVML telemetry queries from the Qt GUI thread via background worker `QThread` and queued Qt signals to eliminate micro-stutters during heavy system load.
