# TCC-G15 Test Strategy & Verification Plan

**Status:** Approved for Cycle 001  
**Author:** QA / Verification Role J (hat)  
**Last Updated:** 2026-11-04  

---

## 1. Test Levels & Execution Matrix

| Level | Scope | Framework / Tool | Mocking Policy | Target Invariants |
|---|---|---|---|---|
| **Level 1: Unit Tests** | Component bounds, bit-packing, sanity filters, whitelist logic | `pytest tests/` | Pure software mocks | INV-1, INV-2, INV-4, INV-5 |
| **Level 2: Integration Tests** | Environment dependencies, imports, WMI wrapper methods | `tools/check_env.py` | Live environment check (fail-safe mock fallback) | INV-3, INV-4 |
| **Level 3: Packaging Smoke Tests** | PyInstaller standalone binary execution, dependencies bundling | `tools/packaged_test.ps1` | Packaged EXE | Runtime stability |
| **Level 4: Hardware-in-the-Loop (HIL)** | Dell USTT mode switching, fan RPM offsets, watchdog recovery | `tools/mode_probe.py`, `tools/watchdog_test.ps1` | Physical hardware (Dell G15 5530) | INV-1, INV-3, INV-6 |

---

## 2. Regression Gate Criteria (Gate G7 Requirements)

Before any PR can be merged to `main`:
1. `pytest tests/ -v` must execute with **100% pass rate** (21+ tests).
2. `python tools/check_env.py` must print `ALL CHECKS PASSED`.
3. No hardware-facing code may execute unverified WMI write commands outside `WMI_MAP.md`.
4. Visual layout bounds test (`test_compact_window_width_between_360_and_400`) must verify compact dimensions.
5. All P0 and P1 defects in cycle scope must have corresponding automated verification tests.
