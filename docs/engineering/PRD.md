# TCC-G15 Cycle 001 Product Requirements Document (PRD)

**Cycle:** 001  
**Target Release:** v1.8.1 (Patch / Integrity & Safety Verification)  
**Status:** Approved for Implementation  
**Author:** Orchestrator Role A  
**QA Lead:** QA Role J  

---

## 1. Requirements Specification

### `REQ-001`: Continuous Integration on Default Branch (`DEF-001`)
- **Problem:** `.github/workflows/ci.yml` is configured for branches `master` and `g15-5530`. The repository default branch is `main`. As a result, CI has never run on `main` or pull requests targeting `main`.
- **Requirement:** Update `.github/workflows/ci.yml` to trigger on `push` to `main` and `pull_request` to `main`.
- **Verification:** Local YAML validation + GitHub Actions run upon push.

### `REQ-002`: Hardware Whitelist Reconciliation & Verification (`DEF-002`)
- **Problem:** README claims Dell G16 7630 and Alienware m15 R7 have "Full Profile & Fan Control", but `SUPPORTED_MODELS` in `DetectHardware.py` omitted them, causing the application to refuse launch without manual override.
- **Requirement:** Add `G16 7630` and `m15 R7` to `SUPPORTED_MODELS` in `src/Backend/DetectHardware.py`. Ensure case-insensitive substring matching succeeds for these models.
- **Verification:** Unit tests in `tests/test_whitelist_and_power.py` verifying that both models are accepted by `DetectHardware.isSupportedModel()`.

### `REQ-003`: Automated Invariant Test for INV-1 Hard Fail-Safe Trip (`DEF-003`)
- **Problem:** Master Directive Invariant INV-1 states that a critical thermal excursion (CPU ≥ 100°C or GPU ≥ 90°C) MUST trip maximum cooling (`G_Mode`) even if the user has disabled the soft fail-safe toggle (`_failsafeOn = False`). While implemented in code, there is no automated regression test guarding this invariant.
- **Requirement:** Add an automated unit test in `tests/test_safety_and_failsafe.py` that verifies the hard emergency trip logic triggers `G_Mode` when `_failsafeOn == False` after `FAILSAFE_HARD_TRIGGER_DELAY_SEC`.
- **Verification:** `pytest tests/test_safety_and_failsafe.py` passes.

### `REQ-004`: Repository Hygiene & Ignored Debug Artifacts (`DEF-004`)
- **Problem:** 44 temporary files (`docs/baseline/*.log`, `docs/baseline/dev.pid`, `docs/restorepoint.txt`, `docs/restorestatus.txt`) are tracked in git, polluting commits and diffs.
- **Requirement:** Untrack all runtime debug logs and PID files from git index (`git rm --cached`). Expand `.gitignore` to prevent any future logging or restore artifacts from being committed.
- **Verification:** `git status` shows no untracked or modified temporary logs; clean repository tree.

### `REQ-005`: Dependency Pinning & Requirement Separation (`DEF-005`)
- **Problem:** `requirements.txt` has loose `>=` lower bounds and mixes developer tools (`pytest`) into production runtime dependencies.
- **Requirement:** Pin exact production versions in `requirements.txt` (`WMI==1.5.1`, `PySide6==6.12.0`, `windows-toasts==1.3.1`, `nvidia-ml-py==12.570.86`, `pywin32==312`). Create `requirements-dev.txt` for development/testing tools (`pytest>=8.0.0`, `ruff`).
- **Verification:** `pip install -r requirements.txt` and `pip install -r requirements-dev.txt` install cleanly.

---

## 2. Traceability Matrix

| Requirement | Defect / Lead ID | Primary File(s) | Verification Test |
|---|---|---|---|
| `REQ-001` | `DEF-001` / `L1` | `.github/workflows/ci.yml` | GitHub Actions CI Execution |
| `REQ-002` | `DEF-002` / `L2` | `src/Backend/DetectHardware.py` | `tests/test_whitelist_and_power.py` |
| `REQ-003` | `DEF-003` / `L4` | `src/GUI/AppGUI.py`, `tests/test_safety_and_failsafe.py` | `test_inv1_hard_failsafe_unbypassable` |
| `REQ-004` | `DEF-004` / `L6` | `.gitignore`, git index | `git ls-files docs/baseline/*.log` = empty |
| `REQ-005` | `DEF-005` / `L7` | `requirements.txt`, `requirements-dev.txt` | `tools/check_env.py` |

---

## 3. Work Breakdown Structure (WBS)
- `TASK-101`: Create git feature branch `cycle-001/p0-safety-claims-ci` from `main`.
- `TASK-102`: Update `.github/workflows/ci.yml` trigger branches to `main`.
- `TASK-103`: Update `src/Backend/DetectHardware.py:SUPPORTED_MODELS` with `G16 7630` and `m15 R7`; update whitelist tests.
- `TASK-104`: Implement `test_inv1_hard_failsafe_unbypassable` in `tests/test_safety_and_failsafe.py`.
- `TASK-105`: Clean git index of 44 tracked temp files and update `.gitignore`.
- `TASK-106`: Pin exact runtime versions in `requirements.txt` and create `requirements-dev.txt`.
- `TASK-107`: Run full regression test suite (`pytest tests/ -v`, `tools/check_env.py`).
- `TASK-108`: Update `README.md`, `CLAIMS.md`, `CHANGELOG.md` to reflect fixes and accurate claim statuses.
- `TASK-109`: Commit changes, push branch, create PR, verify CI, and merge.
