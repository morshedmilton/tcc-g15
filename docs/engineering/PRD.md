# TCC-G15 Cycle 002 Product Requirements Document (PRD)

**Cycle:** 002  
**Target Release:** v1.8.2 (Reliability, Watchdog Sleep Resilience & SBOM)  
**Status:** Approved for Implementation  
**Author:** Orchestrator Role A  
**QA Lead:** QA Role J  
**Safety Lead:** Safety Role E  

---

## 1. Requirements Specification

### `REQ-0201`: Watchdog Sleep / Resume Resilience & GUI Auto-Resurrection (`OPP-002`)
- **Problem:** When Windows enters sleep or modern standby, wall-clock time jumps forward. The watchdog evaluates `time.time() - mtime > 12s`, falsely interprets sleep as an application crash, forces Balanced mode, and terminates. The GUI continues running without any watchdog process monitoring it.
- **Requirement:**
  1. `tcc-watchdog.py` must track monotonic loop duration (`time.monotonic()`). If elapsed time across `time.sleep(POLL_SEC)` exceeds `POLL_SEC + 4.0`, recognize system suspend, log resume event, and grant a grace window equal to `HEARTBEAT_TIMEOUT_SEC`.
  2. `src/GUI/AppGUI.py` must verify `self._watchdog.poll() is None` during each periodic poll. If the watchdog process has exited, automatically call `self._startWatchdog()`.
- **Verification:** Unit test simulating suspend condition and GUI watchdog resurrection.

### `REQ-0202`: Thermal Mode Application Transient Retry (`OPP-003`)
- **Problem:** During heavy system I/O or power transitions, an initial WMI ACPI call to `Thermal_Control` may return a transient failure code or timeout. `ApplyThermalMode` currently permanently caches `False` on the first failure and disables the profile in the UI.
- **Requirement:** `ApplyThermalMode` in `AWCCWmiWrapper.py` must retry a failed `_Thermal_Control` call once after 250ms before permanently concluding that the mode is unsupported.
- **Verification:** Unit test with mock WMI returning False once then 0 on retry.

### `REQ-0203`: Automated Machine-Readable SBOM Generation (`OPP-004`)
- **Problem:** Releases lack a standardized, machine-readable Software Bill of Materials (SBOM) for enterprise software supply chain verification.
- **Requirement:** Integrate `cyclonedx-bom` into `requirements-dev.txt` and `.github/workflows/ci.yml`. Generate `dist/tcc-g15-sbom.json` during the build step and include it in release assets.
- **Verification:** `tcc-g15-sbom.json` generated and validated against CycloneDX schema.

---

## 2. Traceability Matrix

| Requirement | Opportunity ID | Primary File(s) | Verification Test |
|---|---|---|---|
| `REQ-0201` | `OPP-002` | `src/tcc-watchdog.py`, `src/GUI/AppGUI.py` | `tests/test_whitelist_and_power.py::test_watchdog_resurrection_and_suspend_grace` |
| `REQ-0202` | `OPP-003` | `src/Backend/AWCCWmiWrapper.py` | `tests/test_wmi_wrapper.py::test_thermal_mode_apply_retry` |
| `REQ-0203` | `OPP-004` | `.github/workflows/ci.yml`, `requirements-dev.txt` | Build artifact check `dist/tcc-g15-sbom.json` |

---

## 3. Work Breakdown Structure (WBS)
- `TASK-201`: Create git feature branch `cycle-002/watchdog-resilience-sbom`.
- `TASK-202`: Implement suspend detection in `src/tcc-watchdog.py`.
- `TASK-203`: Implement watchdog auto-resurrection in `src/GUI/AppGUI.py`.
- `TASK-204`: Implement transient retry in `src/Backend/AWCCWmiWrapper.py`.
- `TASK-205`: Add CycloneDX to `requirements-dev.txt` and `.github/workflows/ci.yml`.
- `TASK-206`: Write automated tests for watchdog resurrection, suspend grace, and mode apply retry.
- `TASK-207`: Execute regression test suite (`pytest tests/ -v`, `tools/check_env.py`, `ruff check`).
- `TASK-208`: Update documentation (`CHANGELOG.md`, `README.md`, `docs/RELEASE_NOTES_1.8.2.md`).
- `TASK-209`: Package PyInstaller binaries, generate SBOM, build installer, verify checksums.
- `TASK-210`: Commit, push branch, open PR #2, verify CI, squash-merge to `main`, publish pre-release `v1.8.2`.
