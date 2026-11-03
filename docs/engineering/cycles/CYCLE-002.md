# TCC-G15 Engineering Report — Cycle 002

**Cycle:** 002  
**Target Release:** v1.8.2 (Reliability, Watchdog Sleep Resilience & SBOM)  
**Status:** Verification & Packaging  
**Cycle Dates:** 2026-11-04  
**Author:** Multi-disciplinary Autonomous Engineering Organization  

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

---

## 3. Gate Sign-Off Matrix

- **G0 (Delta Reconnaissance):** PASSED (Signed by Orchestrator A, Reviewer L)
- **G1 (Research):** PASSED (Signed by Orchestrator A, Reviewer L)
- **G2 (Forensic Audit):** PASSED (Signed by Safety E, Security I, Reviewer L)
- **G3 (Prioritization & Scope):** PASSED (Signed by Orchestrator A, Reviewer L)
- **G4 (Requirements & Plan):** PASSED (Signed by Orchestrator A, QA J)
- **G5 (Design & ADRs):** PASSED (Signed by Architect B, Safety E, Reviewer L; ADR-002 accepted)
- **G6 (Implementation):** PASSED (Signed by QA J, Reviewer L)
- **G7 (Multi-level Verification):** PASSED (Signed by QA J, Safety E)
- **G8 (Release Engineering & Packaging):** IN_PROGRESS
- **G9 (Cycle Evaluation):** Scheduled

---

## 4. Next Cycle (Cycle 003) Preview
- `OPP-001` (Perf): Background worker thread for telemetry polling (decouple WMI/NVML from GUI thread).
