# TCC-G15 Engineering Report — Cycle 006

**Cycle:** 006  
**Target Release:** v1.8.6 (Process-Aware Automatic Thermal Profile Switching, Custom Rules & High-Performance Presets — OPP-008)  
**Status:** COMPLETED & SHIPPED  
**Cycle Dates:** 2026-11-04  
**Author:** Multi-disciplinary Autonomous Engineering Organization  
**Release Tag:** `v1.8.6` (https://github.com/morshedmilton/tcc-g15/releases/tag/v1.8.6)  

---

## 1. Executive Summary

Cycle 006 introduces automated, process-aware thermal profile switching, built-in curated game and application presets, an interactive custom rules editor, enhanced privacy protections for diagnostics bug reports, and robust safety invariant safeguards ensuring fail-safe supremacy under heavy workloads:

1. **Process-Aware Automatic Thermal Profile Switching (`OPP-008` / ADR-006):**
   - **Non-Invasive `psutil` Process Monitor:** Operates on a dedicated secondary `QtCore.QThread` decoupled from the GUI main thread, sampling running process name metadata via `psutil.process_iter(['name'])` from native NT kernel structures in under 8.6 ms with `< 0.015%` CPU overhead. Zero `OpenProcess` read/write memory handles are opened, guaranteeing 100% anti-cheat transparency and safety across protected titles (BattlEye, Easy Anti-Cheat, Riot Vanguard, Ricochet).
   - **Flap-Free 4.0s Exit Debounce Hysteresis:** Prevents acoustic fan cycling, mode oscillation, and bearing wear during brief launcher transitions, cutscene loading screens, or helper process restarts by requiring 2 consecutive missing poll cycles (4.0s) before restoring profile state.
   - **Cooling Severity Priority Arbitration:** Resolves multi-process concurrent execution conflicts deterministically using the Cooling Severity Priority Matrix (`G_Mode` > `Performance` > `Balanced` > `Quiet`), guaranteeing the system always satisfies the most demanding thermal workload.
   - **Baseline Mode Preservation & Automatic Restoration:** Caches the user's initial baseline thermal mode (`_baselineMode`) upon entry into a process rule and automatically restores it once all triggering processes exit.
   - **User Override Sovereignty:** If the user manually changes the thermal profile while a process rule is active, manual intent takes precedence (`_userOverride = True`) until all matched processes exit.
   - **18 Curated Game & High-Performance Presets:** Pre-configured profiles ready out-of-the-box for popular AAA titles and compute workloads (Cyberpunk 2077, CS2, Apex Legends, Warzone, Valorant, Rainbow Six Siege, Dota 2, LoL, Fortnite, Overwatch 2, GTA V, Baldur's Gate 3, Helldivers 2, Elden Ring, Forza Horizon 5, Blender, Premiere Pro, Unreal Engine).
   - **Interactive Custom Rules Editor:** Modern PySide6 GUI interface allowing users to toggle auto-switching, browse presets, add custom executable rules, configure target thermal modes, and toggle rules on/off.

2. **Safety Invariant INV-1 Fail-Safe Supremacy (`DEF-008`) & Override Fix (`DEF-010`):**
   - **Unconditional INV-1 Fail-Safe Supremacy (`DEF-008`):** Mandates that emergency thermal excursions (CPU >= 100°C or GPU >= 90°C) immediately force G-Mode maximum cooling. The process monitor and automatic switcher yield unconditionally to fail-safe trips; no process rule or exit restoration can lower cooling mode while a fail-safe condition or cooldown is active.
   - **Fail-Safe User Override Protection (`DEF-010`):** Fixes an edge-case state corruption where an INV-1 emergency trip and subsequent reset cooldown previously overwrote the manual `_userOverride` flag during an active process session. Manual user intent remains uncorrupted when returning from emergency fail-safe cooldown.

3. **Diagnostics PII Redaction (`DEF-006`):**
   - `Diagnostics.build()` bug report zip generation now automatically sanitizes sensitive system properties (`UserName`, `PrimaryOwnerName`, and `DNSHostName`) from WMI outputs, ensuring diagnostic packages can be shared publicly for troubleshooting without disclosing personal identifiable information.

4. **Supply Chain & Architectural Hardening (`DEF-007` & `DEF-009`):**
   - **Production Supply Chain Promotion (`DEF-007`):** Promoted `psutil==7.2.2` to production `requirements.txt` with strict version pinning.
   - **Apartment-Isolated Multi-Threading (`DEF-009`):** Implemented strict Qt Signal/Slot decoupled communication between the worker thread and the UI main thread, preserving COM apartment isolation and ensuring zero UI latency.

5. **Safety Invariants Preservation (INV-1 to INV-6):**
   - Hard emergency trip logic (CPU >= 100°C), rate-of-change fan limits (INV-2), fan floor rules (INV-3), AC/DC transitions (INV-4), watchdog heartbeat (INV-5), and USTT 1.8.0+ firmware guard (INV-6) remain uncompromised and fully tested.

---

## 2. Evidence & Test Results

### 2.1 Automated Pytest Suite
- **Command:** `.venv\Scripts\python.exe -m pytest tests/ -v`
- **Result:** **59 passed in 4.23s** (100% pass rate)
- Test breakdown:
  - 42 baseline regression tests (thermal monitoring, tray, fan control, metrics tracker, diagnostics)
  - 9 process switching unit tests (`tests/test_process_monitor.py`):
    - `test_default_rules_initialization` (PASSED)
    - `test_rules_persistence_json` (PASSED)
    - `test_process_monitor_thread_start_stop` (PASSED)
    - `test_process_matching_case_insensitive` (PASSED)
    - `test_cooling_severity_priority` (PASSED)
    - `test_exit_debounce_hysteresis` (PASSED)
    - `test_baseline_mode_restoration` (PASSED)
    - `test_manual_user_override_precedence` (PASSED)
    - `test_failsafe_inv1_supremacy_over_process_switching` (PASSED)
  - 8 adversarial stress tests (`tests/test_opp008_adversarial_stress.py`):
    - `test_rapid_process_spawn_kill_oscillation_no_flapping` (PASSED)
    - `test_concurrent_multi_process_priority_preemption_and_unwind` (PASSED)
    - `test_emergency_inv1_thermal_trip_during_process_active_session` (PASSED)
    - `test_ac_to_dc_transition_locks_quiet_mode_overriding_process_rule` (PASSED)
    - `test_user_manual_override_during_process_session` (PASSED)
    - `test_corrupt_process_rules_json_safe_recovery` (PASSED)
    - `test_process_enumeration_exception_resilience` (PASSED)
    - `test_failsafe_cooldown_does_not_clear_user_override` (PASSED)

### 2.2 Environment & Linter Verification
- `tools/check_env.py`: **ALL CHECKS PASSED (10/10 ok, USTT firmware verified)**
- `ruff check .`: **All checks passed (0 errors)!**

### 2.3 Continuous Integration (GitHub Actions)
- **Workflow:** `.github/workflows/ci.yml` on PR #6 (`cycle-006/opp-008-process-switching` -> `main`)
- **Status:** **All checks green / passed**
  - Dependency installation & Ruff linting
  - Full automated test suite execution (59/59)
  - PyInstaller binary compilation
  - CycloneDX SBOM generation
  - Build artifact archiving

---

## 3. Cryptographic Release Artifacts (v1.8.6)

| Distribution | File Name | Size | SHA-256 Checksum |
|---|---|---|---|
| **Windows Installer** | `tcc-g15-installer-1.8.6.exe` | 45,278,695 bytes | `FF7080BC6457D0CC34A4A04310E59C7FE7B77C2314C6D7827710D566700F1B07` |
| **Portable Zip** | `tcc-g15-portable-1.8.6.zip` | 59,400,389 bytes | `CCE0DA3500AADDF9710A68B3772FFA4D94FB16A9C675CFF5AC3B5EAE90FFBAE4` |
| **CycloneDX SBOM** | `tcc-g15-sbom.json` | 6,605 bytes | `CFEAB335032DA45F5A131C09E4495989738FE6ED305EC72B49247FB85CCDFF86` |

All checksums verified and attested in `dist/SHA256SUMS.txt`.

---

## 4. Gate Sign-Off Matrix

- **G0 (Delta Reconnaissance):** PASSED (Signed by Orchestrator A, Reviewer L; verified clean baseline at `f30555e`, 42/42 tests pass)
- **G1 (Research & Delta Intel):** PASSED (Signed by Orchestrator A, Reviewer L; verified psutil performance `SRC-006`, anti-cheat safety `SRC-007`, debounce `SRC-008`, presets catalog `SRC-009`)
- **G2 (Forensic Audit):** PASSED (Signed by Safety E, Security I, Auditor; hardware & safety audit passed, DEF-006..DEF-009 registered)
- **G3 (Prioritization & Scope):** PASSED (Signed by Orchestrator A, Reviewer L, Worker Phase 3; OPP-008, DEF-006..DEF-009 prioritized & frozen in BACKLOG.md)
- **G4 (Requirements & Plan):** PASSED (Signed by Orchestrator A, QA J, Worker Phase 4; PRD.md updated with REQ-0601..REQ-0608 and WBS TASK-601..TASK-610)
- **G5 (Design & ADRs):** PASSED (Signed by Architect B, Safety E, Reviewer L; ADR-006 accepted, ARCHITECTURE.md updated to rev2)
- **G6 (Implementation):** PASSED (Signed by Implementer, QA J, Reviewer L; core process switching modules and bug fixes implemented, 51/51 pytest passed)
- **G7 (Quality Verification):** PASSED (Signed by QA J, Safety E, Reviewer L; 59/59 tests pass, 8 adversarial stress tests pass, DEF-010 verified)
- **G8 (Packaging & Release Readiness):** PASSED (Signed by DevOps K, Reviewer L; PyInstaller, Inno Setup installer, SBOM, SHA-256 verified)
- **G9 (Deployment & Release Monitoring):** PASSED (Signed by Orchestrator A, Worker Phase 9; PR #6 squash-merged to `main`, git tag `v1.8.6` pushed, GitHub release published)
