# TCC-G15 Evolution Engineering Control State

**Cycle:** 007  
**Target Release:** v1.8.7 (Auto profile restored, four-profile selector, audit fixes)  
**Current Git Branch:** `cycle-007/auto-profile`  
**Status:** IN PROGRESS (G6 verification complete locally; G8 packaging + G9 release pending)  
**Last Updated:** 2026-11-04T17:05:00+06:00  

---

## 1. Gate Status Matrix

| Gate | Description | Signed By | Status | Evidence / Notes |
|---|---|---|---|---|
| **G0** | Delta Reconnaissance | Orchestrator, Reviewer L | **PASSED** | Clean git tree on `main` at `f30555e`, 42/42 tests pass, check_env 10/10 ok, ruff clean, CLAIMS.md audited, INV-1..INV-6 verified (`.agents/teamwork/orchestrator/GATE_STATUS.md`) |
| **G1** | Research & Delta Intel | Orchestrator, Reviewer L | **PASSED** | `SRC-006` (process enumeration benchmark: psutil 8.59ms vs WMI 1743ms), `SRC-007` (anti-cheat non-invasive matching), `SRC-008` (anti-flapping 4s debounce & baseline restoration), `SRC-009` (presets catalog for 18 games/apps) verified in `docs/engineering/RESEARCH.md` |
| **G2** | Forensic Audit (Delta) | Forensic Auditor, Safety E | **PASSED** | Hardware & safety audit for OPP-008 (INV-1..INV-6 verified, raw EC 0x66/0x68 absent, UAC elevated, DEF-001..DEF-005 verified remediated, DEF-006..DEF-009 registered in AUDIT.md) |
| **G3** | Prioritization & Scope | Orchestrator, Reviewer L, Worker Phase 3 | **PASSED** | OPP-008, DEF-006, DEF-007, DEF-008, DEF-009 scored via Master Directive formula; Scope frozen in BACKLOG.md; Rejected register updated |
| **G4** | Requirements & Traceability | Orchestrator, QA J, Worker Phase 4 | **PASSED** | PRD.md updated with REQ-0601..REQ-0608 (OPP-008, DEF-006..DEF-009), 100% bidirectional traceability matrix, 18 curated presets, WBS TASK-601..TASK-610 |
| **G5** | System Design & ADRs | Architect B, Safety E, Reviewer L | **PASSED** | ADR-006 created with complete architecture, Cooling Severity Priority Matrix, 4.0s debounce, state restoration, and INV-1 supremacy; ARCHITECTURE.md updated to rev2 with multi-threaded model and process subsystem diagrams |
| **G6** | Implementation Verification | Implementer, QA J, Reviewer L | **PASSED** | OPP-008 modules implemented on branch `cycle-006/opp-008-process-switching`; 51/51 pytest passed, ruff clean (0 violations), check_env 10/10 ok |
| **G7** | Multi-level Verification & HIL | QA J, Safety E, Reviewer L | **PASSED** | 59/59 pytest passed, 8 adversarial stress suites passing, ruff clean (0 violations), check_env 10/10 ok, DEF-010 verified (`reviewer_phase7_final/handoff.md`) |
| **G8** | Release Engineering & Packaging | DevOps K, Reviewer L | **PASSED** | PyInstaller onedir GUI (`dist/tcc-g15`), onefile watchdog (`dist/tcc-watchdog.exe`), Inno Setup installer (`tcc-g15-installer-1.8.6.exe`), portable zip (`tcc-g15-portable-1.8.6.zip`), CycloneDX SBOM (`tcc-g15-sbom.json`), SHA256SUMS.txt verified |
| **G9** | Cycle Evaluation & Learning | Orchestrator A, Worker Phase 9 | **PASSED** | PR #6 squash-merged to `main`, tag `v1.8.6` pushed, GitHub release `v1.8.6` published with verified assets |

---

## 2. Active Tasks & Status

| Task ID | Description | Role | Status | Evidence |
|---|---|---|---|---|
| `TASK-601` | Phase 0 Delta Reconnaissance & Safety Invariant baseline audit | Spec Miner / Explorer | **DONE** | Gate G0 passed; reports produced |
| `TASK-602` | Phase 1 Research & Delta Intelligence (SRC-006 to SRC-009) | Research Lead / Implementer | **DONE** | Gate G1 passed; RESEARCH.md updated |
| `TASK-603` | Phase 2 Forensic Hardware & Safety Audit | Safety E / Security I / Auditor | **DONE** | Gate G2 passed; AUDIT.md and handoff.md completed |
| `TASK-604` | Phase 3 Prioritization & Scope Selection | Orchestrator / Worker Phase 3 | **DONE** | Gate G3 passed; BACKLOG.md scored and frozen; STATE.md updated |
| `TASK-605` | Phase 4 Requirements Engineering & Traceability (PRD.md) | Orchestrator / QA J / Worker Phase 4 | **DONE** | PRD.md updated with REQ-0601..REQ-0608, traceability matrix, WBS; Gate G4 passed |
| `TASK-606` | Phase 5 System Design & Architecture (ADR-006) | Architect B / Safety E | **DONE** | Gate G5 passed; ADR-006 and ARCHITECTURE.md updated and verified |
| `TASK-607` | Phase 6 Feature Branch Implementation | Implementer / QA J | **DONE** | Gate G6 passed; all OPP-008 modules, DEF-006, DEF-007, DEF-008, DEF-009 implemented & verified |
| `TASK-608` | Phase 7 Multi-Level Automated QA & Safety Verification | QA J / Safety E | **DONE** | Gate G7 passed; 59/59 tests pass, DEF-010 verified |
| `TASK-609` | Phase 8 Packaging & Release Engineering | DevOps K | **DONE** | Gate G8 passed; all v1.8.6 release artifacts & checksums generated |
| `TASK-610` | Phase 9 PR, CI, Merge, Tag v1.8.6, Release Publishing | Orchestrator A / Worker Phase 9 | **DONE** | PR #6 squash-merged, CI passed, tag v1.8.6 pushed, GitHub release published |

---

## 2b. Cycle 007 Working Notes (append-only for resumability)

- **Owner directive (2026-11-04):** exactly four profiles — `Auto`, `Balanced`, `G-Mode`, `Custom`;
  Auto = temperature-driven fan curve (50 °C ≈ 3500 rpm, 80 °C+ = full speed); fix the broken/clipped UI.
- **Delivered on branch `cycle-007/auto-profile`:** `src/Backend/FanCurve.py` (new), Auto wiring in
  `AppGUI`, four-visible-profile selector (hidden profiles stay programmatically selectable),
  `ProcessRule.with_visible_target()` + `_as_bool`, `SUPPORTED_MODES` aligned, window sizing fixed
  (574x234 on hardware), version 1.8.7, CHANGELOG entry, `cycles/CYCLE-007.md`.
- **Verified locally:** `pytest tests/ -q` → 82 passed; `ruff check .` clean; `tools/check_env.py` PASS;
  hardware launch + screenshot `docs/baseline/cycle007-h196.png`.
- **Open, NOT fixed in 007 (next cycle):** DEF-716 (TACH shows 0 RPM while hardware reports ~2100),
  DEF-701 (manual click during latched fail-safe is discarded), DEF-703/705/706/707/709/710/712-715.
- **Audit source:** `docs/engineering/audit/CYCLE-007/backend-process-switching.md` (child agent,
  partially completed; findings were re-verified against the tree before use).
- **Next Action:** package 1.8.7 (PyInstaller + Inno + SBOM + SHA256), PR -> CI green -> squash merge
  -> tag `v1.8.7` -> pre-release, then start Cycle 008 on DEF-716 first.

## 3. Owner Actions Required
*None. Autonomous execution under Master Directive §0.*

---

## 4. Current Cycle 006 Scope (OPP-008 & Invariant Fixes)
- **Prime Scope:** `OPP-008` (Process-Aware Automatic Thermal Profile Switching, Custom Rules, 18 Game/App Presets, 4s exit debounce hysteresis, Cooling Severity Priority Matrix).
- **Mandatory Safety & Architecture Fixes:**
  - `DEF-008` (P0): Unconditional INV-1 Hard Fail-Safe Supremacy in OPP-008 switching logic.
  - `DEF-006` (P1): Diagnostics PII Redaction for `UserName`, `PrimaryOwnerName`, and `DNSHostName`.
  - `DEF-007` (P1): Promote `psutil==7.2.2` to production `requirements.txt`.
  - `DEF-009` (P1): Dedicated QThread and Qt Signal/Slot COM apartment isolation.
  - `DEF-010` (P0): Prevent INV-1 emergency fail-safe trip and cooldown from corrupting user override state (`_userOverride`) during active process rule sessions.
