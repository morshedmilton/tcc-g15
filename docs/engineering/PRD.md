# TCC-G15 Product Requirements Document (PRD) — Cycle 006

**Cycle:** 006  
**Target Release:** v1.8.6 (Process-Aware Automatic Thermal Profile Switching & Custom Rules — OPP-008)  
**Status:** Approved for Implementation (Gate G4 Satisfied)  
**Author:** Requirements Lead (Worker Phase 4)  
**QA Lead:** QA Role J  
**Safety Lead:** Safety Role E  

---

## 1. Requirements Specification

### `REQ-0601`: Process Detection Engine (`OPP-008`, `DEF-009`)
- **Problem Statement:**
  Gamers and content creators frequently switch between light productivity and heavy compute/gaming workloads. Manually switching thermal modes each time is inconvenient and often forgotten, resulting in unnecessary acoustic fan noise during desktop tasks or thermal throttling under heavy games. Existing attempts at process polling via synchronous WMI queries incur severe latency (~1,743 ms) and high CPU spikes (~3–8% overhead), which block the GUI thread and degrade system responsiveness.
- **Requirement:**
  1. Create `ProcessMonitorWorker` inheriting from `QObject` designed to execute in a dedicated secondary `QThread` decoupled from the PySide6 GUI thread.
  2. Implement process scanning using `psutil.process_iter(['name'])` at a fixed cadence of 2.5 seconds (2500 ms).
  3. Ensure non-invasive matching: the worker MUST query solely the `['name']` attribute from global Windows NT kernel tables (`SystemProcessInformation`). The worker MUST NEVER request `['exe']`, `['cmdline']`, or `['environ']`, and MUST NEVER call `OpenProcess` with read, write, or memory inspection rights, ensuring total transparency across kernel-level anti-cheat software (BattlEye, Easy Anti-Cheat, Riot Vanguard, Ricochet).
  4. Encapsulate process scanning in robust exception handling (`psutil.NoSuchProcess`, `psutil.AccessDenied`, `psutil.ZombieProcess`, `Exception`) to ensure transient process terminations never abort the worker loop or starve the thread.
  5. Emit a Qt signal (e.g. `processes_scanned = Signal(set)`) delivering the set of lowercase active process names to the main GUI thread, isolating COM apartment threading (`DEF-009`).
- **Acceptance Criteria:**
  - `AC-0601.1`: `ProcessMonitorWorker` operates continuously on a secondary `QThread` without blocking GUI responsiveness or event handling.
  - `AC-0601.2`: Mean process scan execution time across all system processes is < 25 ms and idle CPU utilization is < 0.05% at 2.5s polling cadence.
  - `AC-0601.3`: The detection engine accesses only process name metadata and does not open privileged handles, inject code, or read target process memory.
  - `AC-0601.4`: Ephemeral process termination or permissions errors during scanning are caught and handled without terminating the worker thread.

---

### `REQ-0602`: Dynamic Rule Matching, Precedence & State Restoration (`OPP-008`)
- **Problem Statement:**
  When multiple configured applications run simultaneously or in staggered sequences (e.g. launching a game while background rendering is active), naive switching logic causes state collisions, mode flapping, and loss of the user's original idle thermal profile. Furthermore, if a user manually adjusts thermal settings during a game session, automatic logic must not override their explicit intent.
- **Requirement:**
  1. Define a structured `ProcessRule` data model containing `process_name: str` (case-insensitive executable basename), `target_mode: str` (valid Alienware thermal mode), `enabled: bool`, and optional `description: str`.
  2. Implement the **Cooling Severity Priority Matrix** for multi-process arbitration. If multiple active processes match enabled rules, select the mode offering maximum cooling capacity:
     $$\text{G\_Mode (0xAB)} > \text{Performance (0xA1)} > \text{Custom (0x0)} > \text{Balanced (0xA0)} > \text{Quiet (0xA3)}$$
  3. Implement **Baseline Mode Preservation**:
     - Capture `_baselineMode` from the current active thermal mode ONLY upon the transition from zero active matching rules to one or more active matching rules.
     - While any matching rule remains active, subsequent process launches or state re-evaluations MUST NOT overwrite `_baselineMode`.
  4. Implement **State Restoration**:
     - When all matching processes have terminated (subject to exit debouncing in `REQ-0603`), automatically restore the thermal mode to `_baselineMode`.
     - Reset `_baselineMode` to `None` upon successful restoration.
  5. Implement **Manual User Override Handling**:
     - If the user manually changes the thermal profile in the GUI or toggles the Alienware G-Key while an automated process rule is active, set `_userOverride = True`.
     - While `_userOverride` is active, suppress all automated profile switching for the duration of the current matching session.
     - When all matching processes exit and exit debouncing completes, reset `_userOverride = False` and clear `_baselineMode` without disturbing the user's manually chosen mode.
- **Acceptance Criteria:**
  - `AC-0602.1`: Detecting an active matching process automatically transitions the system to its configured thermal profile.
  - `AC-0602.2`: When multiple matching processes run concurrently, the profile with highest cooling priority is selected according to the Cooling Severity Priority Matrix.
  - `AC-0602.3`: `_baselineMode` is captured exclusively on the 0-to-1 match transition and is reliably restored when all matching processes close.
  - `AC-0602.4`: Manual profile changes during an active rule session set `_userOverride = True`, preventing further automated profile changes until all matched processes exit.

---

### `REQ-0603`: Anti-Flapping Exit Hysteresis (`OPP-008`)
- **Problem Statement:**
  PC games frequently restart worker binaries or temporarily disappear from process listings during intro cutscenes, resolution changes, anti-cheat handoffs, or level transitions. Reverting the thermal profile immediately upon process disappearance causes rapid fan deceleration followed seconds later by violent acceleration ("fan flapping"), causing severe acoustic annoyance and mechanical wear on fan bearings.
- **Requirement:**
  1. Implement an exit debounce hysteresis filter of **4.0 seconds (or 2 consecutive polling cycles absent)** before treating a matched process as terminated.
  2. Maintain a per-rule or global missing-cycle counter/timestamp. When a previously active matched process is absent from a scan, increment its missing counter.
  3. If the process reappears within the 4.0-second debounce window, reset the missing counter; maintain the active high-performance thermal mode without interruption.
  4. Only when all matching processes have remained continuously absent for >= 4.0 seconds (2 consecutive polling cycles) shall the state restoration logic in `REQ-0602` be triggered.
- **Acceptance Criteria:**
  - `AC-0603.1`: Monitored processes absent for < 4.0 seconds do not trigger profile reversion or fan speed changes.
  - `AC-0603.2`: Reversion to `_baselineMode` occurs reliably after all matching processes have remained absent continuously for at least 4.0 seconds (2 consecutive poll intervals).
  - `AC-0603.3`: Re-emergence of the process within the 4.0s window resets the debounce timer and preserves the active profile.

---

### `REQ-0604`: Curated Out-of-the-Box Presets (`OPP-008`)
- **Problem Statement:**
  Requiring users to manually locate and configure executable basenames for every game creates friction and reduces feature adoption. Users require an out-of-the-box catalog of verified presets for popular games and creator applications.
- **Requirement:**
  1. Ship a curated catalog of 18 default rules across AAA Gaming, Competitive Esports, and Content Creation / Benchmarking matching `SRC-009`:
     - **AAA Gaming:**
       - `cyberpunk2077.exe` -> `G_Mode`
       - `gta5.exe` -> `Performance`
       - `rdr2.exe` -> `G_Mode`
       - `eldenring.exe` -> `Performance`
       - `bg3.exe` (and `bg3_dx11.exe`) -> `Performance`
     - **Competitive Esports:**
       - `cs2.exe` -> `Performance`
       - `r5apex.exe` -> `Performance`
       - `valorant-win64-shipping.exe` -> `Performance`
       - `fortniteclient-win64-shipping.exe` -> `Performance`
       - `overwatch.exe` -> `Performance`
       - `cod.exe` -> `G_Mode`
     - **Content Creation & Benchmarking:**
       - `blender.exe` -> `Performance`
       - `premiere.exe` -> `Performance`
       - `afterfx.exe` -> `Performance`
       - `resolve.exe` -> `Performance`
       - `handbrake.exe` -> `Performance`
       - `cinebench.exe` -> `G_Mode`
       - `3dmark.exe` -> `G_Mode`
  2. Curated presets must be initialized automatically on clean installation or when no user configuration exists.
  3. Individual presets may be enabled, disabled, or customized by the user.
- **Acceptance Criteria:**
  - `AC-0604.1`: Clean installation initializes all 18 curated presets enabled by default.
  - `AC-0604.2`: Target executable names and thermal profiles match the curated specification exactly.
  - `AC-0604.3`: Users can enable or disable individual preset rules without deleting them.

---

### `REQ-0605`: Rule Management UI & Configuration Persistence (`OPP-008`)
- **Problem Statement:**
  Users must be able to view current rules, toggle automation globally or per rule, add custom games/applications, and persist their customizations across reboots.
- **Requirement:**
  1. Implement a `ProcessRulesDialog` (accessible from `AppGUI`) featuring:
     - Global master toggle: "Enable Automatic Thermal Switching".
     - Table widget displaying Rule Name, Executable Basename, Target Thermal Mode, and Enabled checkbox.
     - Action buttons: "Add Rule", "Edit Rule", "Remove Rule", "Reset to Defaults".
  2. Serialize and persist configuration using `QSettings` under application key `process_rules` (JSON format) and `auto_switch_enabled` (boolean).
  3. Ensure custom rules enforce valid executable names (sanitizing `.exe` suffix and whitespace) and valid thermal modes from `ThermalMode`.
- **Acceptance Criteria:**
  - `AC-0605.1`: UI displays all active rules with clear visual status of enabled/disabled state.
  - `AC-0605.2`: Users can add custom rules with custom executable names and select any valid thermal profile.
  - `AC-0605.3`: Toggling the global master switch completely pauses or resumes background process monitoring.
  - `AC-0605.4`: All rule additions, modifications, deletions, and toggle states persist across application restarts via `QSettings`.
  - `AC-0605.5`: "Reset to Defaults" restores the 18 curated presets after user confirmation.

---

### `REQ-0606`: Unconditional INV-1 Hard Fail-Safe Supremacy (`DEF-008`)
- **Problem Statement:**
  Safety Invariant INV-1 mandates that a critical thermal excursion (CPU >= 100°C or GPU >= 90°C) forces `G_Mode` maximum cooling. If an automated process rule were permitted to apply a lower profile (e.g. `Performance`, `Balanced`, or `Quiet`) or attempt baseline restoration while fail-safe is engaged, hardware could be damaged.
- **Requirement:**
  1. Process-aware profile switching logic MUST unconditionally yield to Safety Invariant INV-1.
  2. When the hard fail-safe engages (`_failsafeTrippedPrevModeStr is not None`), all process rule switching and baseline restoration actions MUST be strictly locked out.
  3. During the 60-second fail-safe reset cooldown, automated process profile modifications remain completely disabled.
  4. If a matching process exits while fail-safe is active, baseline restoration MUST NOT lower the fan speed or revert mode; the fail-safe recovery logic retains sole authority over mode restoration.
- **Acceptance Criteria:**
  - `AC-0606.1`: An active hard fail-safe trip locks out all process rule profile changes.
  - `AC-0606.2`: No automated rule can transition the system out of `G_Mode` while `_failsafeTrippedPrevModeStr is not None`.
  - `AC-0606.3`: Unit tests prove that process launch or termination during an active fail-safe event does not disrupt emergency cooling.

---

### `REQ-0607`: Diagnostics Privacy Redaction (`DEF-006`)
- **Problem Statement:**
  Forensic audit discovered that `src/GUI/Diagnostics.py` dumps `Win32_ComputerSystem` containing unredacted PII (`UserName` with domain/username, `PrimaryOwnerName` with user email address, and `DNSHostName`), directly violating privacy commitments stated in the module docstrings.
- **Requirement:**
  1. Update `src/GUI/Diagnostics.py` to redact sensitive identifying fields in WMI queries.
  2. Extend `_PYSIDE_REDACT_KEYS` / redaction filter to include:
     `'username'`, `'primaryownername'`, `'dnshostname'`, `'workgroup'`, `'domain'`.
  3. Redacted field values in `wmi.json` within the generated diagnostics zip must be replaced with `"[REDACTED]"`.
- **Acceptance Criteria:**
  - `AC-0607.1`: Generating a diagnostics bundle produces a `wmi.json` where `UserName`, `PrimaryOwnerName`, and `DNSHostName` are strictly redacted.
  - `AC-0607.2`: Automated regression test asserts that none of the target PII fields contain raw host, user, or email strings.

---

### `REQ-0608`: Production Supply Chain Pinned Dependency (`DEF-007`)
- **Problem Statement:**
  `psutil==7.2.2` is currently pinned in `requirements-dev.txt` but omitted from `requirements.txt`. Because OPP-008 utilizes `psutil` at runtime in production, running without it in production environments or missing it in PyInstaller bundles would cause fatal `ImportError` crashes.
- **Requirement:**
  1. Promote `psutil==7.2.2` to `requirements.txt` under production dependencies.
  2. Ensure `requirements-dev.txt` references or maintains compatible pins.
  3. Ensure `tools/check_env.py` and PyInstaller build configuration bundle `psutil` cleanly into standalone distribution packages.
- **Acceptance Criteria:**
  - `AC-0608.1`: `requirements.txt` contains `psutil==7.2.2` pinned with exact `==` version specification.
  - `AC-0608.2`: `python tools/check_env.py` passes with `psutil` validated.
  - `AC-0608.3`: Standalone PyInstaller build successfully imports `psutil` at runtime.

---

## 2. Traceability Matrix

| Requirement | Opportunity / Defect ID | Primary File(s) | Verification Test(s) |
|---|---|---|---|
| `REQ-0601` | `OPP-008` / `DEF-009` | `src/GUI/ProcessMonitorWorker.py`, `src/GUI/AppGUI.py` | `tests/test_process_monitor.py::test_process_monitor_scanning_and_signal` |
| `REQ-0602` | `OPP-008` | `src/Backend/ProcessRule.py`, `src/GUI/AppGUI.py` | `tests/test_process_monitor.py::test_dynamic_rule_matching_priority_and_restoration`<br>`tests/test_process_monitor.py::test_manual_user_override` |
| `REQ-0603` | `OPP-008` | `src/Backend/ProcessRule.py`, `src/GUI/AppGUI.py` | `tests/test_process_monitor.py::test_anti_flapping_exit_hysteresis` |
| `REQ-0604` | `OPP-008` | `src/Backend/ProcessRulePresets.py` | `tests/test_process_monitor.py::test_curated_presets_catalog_and_defaults` |
| `REQ-0605` | `OPP-008` | `src/GUI/ProcessRulesDialog.py`, `src/GUI/AppGUI.py` | `tests/test_process_monitor.py::test_rules_persistence_qsettings` |
| `REQ-0606` | `DEF-008` | `src/GUI/AppGUI.py` | `tests/test_process_monitor.py::test_inv1_hard_failsafe_supremacy_over_rules` |
| `REQ-0607` | `DEF-006` | `src/GUI/Diagnostics.py` | `tests/test_process_monitor.py::test_diagnostics_privacy_redaction_def006` |
| `REQ-0608` | `DEF-007` | `requirements.txt`, `tools/check_env.py` | `tests/test_process_monitor.py::test_psutil_pinned_dependency` |

---

## 3. Work Breakdown Structure (WBS)

- `TASK-601`: Phase 0 Delta Reconnaissance & Safety Invariant baseline audit (Gate G0 - DONE).
- `TASK-602`: Phase 1 Research & Delta Intelligence: process enumeration benchmarks, anti-cheat safety, debouncing, and presets catalog (`SRC-006`..`SRC-009`) (Gate G1 - DONE).
- `TASK-603`: Phase 2 Forensic Hardware & Safety Audit: INV-1..INV-6 verification, DEF-001..DEF-005 verification, DEF-006..DEF-009 registration (Gate G2 - DONE).
- `TASK-604`: Phase 3 Prioritization & Scope Selection: mathematical scoring, frozen scope definition, and rejected register formalization (Gate G3 - DONE).
- `TASK-605`: Phase 4 Requirements Engineering & Traceability: define `REQ-0601`..`REQ-0608`, acceptance criteria, bidirectional traceability matrix, and WBS in `PRD.md` (Gate G4 - DONE).
- `TASK-606`: Phase 5 System Design & Architecture: author ADR-006, define QThread signal/slot architecture, update `ARCHITECTURE.md` (Gate G5 - ACTIVE).
- `TASK-607`: Phase 6 Feature Branch Implementation: create `cycle-006/...`, implement `ProcessRule`, `ProcessRulePresets`, `ProcessMonitorWorker`, `ProcessRulesDialog`, `AppGUI` integration, `Diagnostics.py` PII redaction (`DEF-006`), and `requirements.txt` update (`DEF-007`) (Gate G6).
- `TASK-608`: Phase 7 Multi-Level Automated QA & Safety Verification: create comprehensive `tests/test_process_monitor.py`, run pytest regression suite, verify static analysis with ruff, and validate hardware guards (Gate G7).
- `TASK-609`: Phase 8 Packaging & Release Engineering: build PyInstaller standalone executable, generate CycloneDX SBOM, build Inno Setup installer v1.8.6, compute SHA-256 hashes (Gate G8).
- `TASK-610`: Phase 9 PR Creation, CI Verification, Merge, Tag `v1.8.6`, and GitHub Release Publishing (Gate G9).
