# TCC-G15 Forensic Code, Safety & Security Audit

**Historical Baseline Date:** 2026-11-04 (Target: Git `6e7ad43`)  
**Cycle 006 Delta Audit Date:** 2026-11-04 (Target: Git `f30555e`)  
**Auditors:** Forensic Safety Auditor (`teamwork_auditor`), Safety Engineer E, Security Role I, Reviewer L  
**Gate:** G2 (Forensic Hardware & Safety Audit) — Cycle 006 (OPP-008)  

---

## 1. Safety Invariants Compliance Audit (Active Baseline Verification)

Every Safety Invariant INV-1 through INV-6 was independently inspected in source code, empirically verified against runtime behavior, and confirmed via automated test suites.

| Invariant | Description | Source Code Location | Verification Evidence | Status |
|---|---|---|---|---|
| **INV-1** | Hard emergency fail-safe trips to G-Mode (`0xAB`) upon critical CPU >= 100°C or GPU >= 90°C excursion sustained for > 4.0s, bypassing user soft toggle | `src/GUI/AppGUI.py:260-263, 663-693` | `tests/test_safety_and_failsafe.py:40-107` (`test_inv1_hard_failsafe_unbypassable`) executes mock hardware excursion with `_failsafeOn = False` and verifies forced `G_Mode` trip. | **PASS (VERIFIED)** |
| **INV-2** | Temperature sanity filter (5°C–120°C) discards bogus readings (Dell 2–3°C dGPU low-power bug) and triggers fail-safe on sensor absence > 60s | `src/GUI/AppGUI.py:265, 650-661, 943-944` | `tests/test_safety_and_failsafe.py:7-22` (`test_temperature_sanity_filter`), `tests/test_telemetry_worker.py:12-22`. | **PASS (VERIFIED)** |
| **INV-3** | Detached watchdog restores firmware-safe Balanced mode (`0xA0`) on GUI crash/kill/hang within 12s, resilient to Modern Standby | `src/tcc-watchdog.py:17-18, 47-50, 60-69`, `src/GUI/AppGUI.py:830-893` | `tests/test_whitelist_and_power.py:26-54` (`test_watchdog_resurrection`, `test_watchdog_command_structure`). Watchdog checks monotonic elapsed time > 6s for sleep detection. | **PASS (VERIFIED)** |
| **INV-4** | Fan speed offset sliders clamped strictly to 0%–100% in GUI and WMI driver interface | `src/Backend/AWCCWmiWrapper.py:105-109`, `src/GUI/ThermalUnitWidget.py:135-140` | `tests/test_ui_refinements.py:18-56` (`test_offs_slider_limits_0_to_100`). Clamped to min(100, val). | **PASS (VERIFIED)** |
| **INV-5** | Hardware SMBIOS whitelist rejects unsupported hardware unless explicit override `TCC_ALLOW_UNSUPPORTED=1` is provided | `src/Backend/DetectHardware.py:8-12, 34-41`, `src/GUI/AppGUI.py:1028-1033` | `tests/test_whitelist_and_power.py:7-24` (`test_hardware_whitelist`, `test_hardware_whitelist_env_override`). | **PASS (VERIFIED)** |
| **INV-6** | Monotonic cooling floor: fan offset can only increase above EC curve (zero raw EC port access, no direct ring-0 kernel port writes), and COM apartment isolation enforced | Dell EC Firmware + `src/Backend/AWCCWmiWrapper.py:108`, `src/GUI/TelemetryWorker.py:67, 174` | Repo-wide search confirms 0 instances of raw I/O port writes (`0x66`/`0x68`, `inb`/`outb`, `WinRing0`). Positive additive offsets only. `pythoncom.CoInitialize()` and `CoUninitialize()` isolate COM apartments across threads. | **PASS (VERIFIED)** |

---

## 2. Historical Defect Register Re-Audit (DEF-001 through DEF-005)

All 5 historical defects identified in initial baseline audits were verified in the codebase for complete remediation:

1. **`DEF-001` (P0 - Critical): CI Workflow Branch Trigger Mismatch**
   - **Remediation Status:** **VERIFIED CLOSED**
   - **Evidence:** `.github/workflows/ci.yml:4-7` explicitly specifies `branches: [ "main" ]` for both `push` and `pull_request`. GitHub Actions actively targets `main`.
2. **`DEF-002` (P0 - Critical): Hardware Whitelist Missing Compatible Models**
   - **Remediation Status:** **VERIFIED CLOSED**
   - **Evidence:** `src/Backend/DetectHardware.py:10` includes `'G16 7630'` and `'m15 R7'`. Verified by `tests/test_whitelist_and_power.py:test_hardware_whitelist`.
3. **`DEF-003` (P0 - Critical): Missing Unit Test for INV-1 Hard Fail-Safe Trip**
   - **Remediation Status:** **VERIFIED CLOSED**
   - **Evidence:** `tests/test_safety_and_failsafe.py:40-107` (`test_inv1_hard_failsafe_unbypassable`) mocks a hardware thermal excursion and validates unbypassable trip to `G_Mode` even with `_failsafeOn=False`.
4. **`DEF-004` (P1 - High): Tracked Debug/Log Files in Repository Index**
   - **Remediation Status:** **VERIFIED CLOSED**
   - **Evidence:** Git working directory clean; `.gitignore` ignores `*.log`, `*.zip`, `*.csv`, `dist/`, `build/`.
5. **`DEF-005` (P1 - High): Unpinned Dependencies & Mixed Dev/Runtime Requirements**
   - **Remediation Status:** **VERIFIED CLOSED**
   - **Evidence:** `requirements.txt` strictly pins production runtime packages (`WMI==1.5.1`, `PySide6==6.12.0`, `Windows-Toasts==1.3.1`, `nvidia-ml-py==13.615.71`, `pywin32==312`). Development/test packages (`pytest`, `pyinstaller`, `cyclonedx-bom`, `psutil`) isolated in `requirements-dev.txt`.

---

## 3. Forensic Safety & Risk Analysis for OPP-008 (Process-Aware Profile Switching)

An adversarial failure mode and effects analysis (FMEA) was conducted for OPP-008 Process-Aware Automatic Profile Switching:

### 3.1 Failure Modes & Invariant Conflict Analysis
1. **INV-1 Conflict (Hard Fail-safe Override Hazard):**
   - *Hazard:* A background process rule triggers a switch to `Performance`, `Custom`, or `Quiet` while the machine is actively undergoing a critical thermal emergency (CPU >= 100°C or GPU >= 90°C).
   - *Mitigation & Gate Rule:* The process switching engine MUST yield unconditionally to fail-safe trips. When `_failsafeTrippedPrevModeStr is not None` or fail-safe is actively triggered, process switching is completely locked out. No automated rule may set or restore modes until the 60s fail-safe reset cooldown has completed.
2. **INV-2 Conflict (Sensor Degradation / Timeout):**
   - *Hazard:* In the event of sensor dropouts exceeding 60s, soft fail-safe triggers G-Mode. If a process rule evaluates simultaneously, it could restore a lower mode.
   - *Mitigation & Gate Rule:* Automatic profile switching must check `_failsafeTrippedPrevModeStr` and sensor health flags before applying mode adjustments.
3. **INV-3 Conflict (Watchdog Starvation via Process Scan Latency):**
   - *Hazard:* If process scanning blocks the main thread for > 12s, the detached watchdog will conclude the GUI hung and force-apply `Balanced` mode.
   - *Mitigation & Gate Rule:* `psutil.process_iter(['name'])` completes in 8.59ms (empirically benchmarked in physical testing), well within the 2000ms poll cycle. Furthermore, process scanning must be encapsulated with broad exception handling (`except Exception`) so process inspection errors never abort the GUI event loop or starve the watchdog heartbeat.

### 3.2 Race Conditions, Anti-Flapping & Thread Safety
1. **Multi-Process Arbitration (Cooling Severity Priority Matrix):**
   - When multiple target processes run simultaneously with disparate profiles, the engine must select the mode offering maximum cooling capacity:
     $$G\_Mode (0xAB) > Performance (0xA1) > Custom (0x0) > Balanced (0xA0) > Quiet (0xA3)$$
2. **Exit Debounce Hysteresis:**
   - To eliminate mode flapping during game scene transitions or client restarts, an exit debounce window of at least 4.0 seconds (or 2 consecutive polling cycles) must elapse before restoring the baseline profile.
3. **Thread Safety & COM Isolation:**
   - Background worker threads must communicate via Qt Signals/Slots to the main GUI thread for mode switching, preventing `RPC_E_WRONG_THREAD` COM RPC marshalling exceptions.

### 3.3 Security, UAC Manifest & Supply Chain Audit
1. **UAC Elevation:**
   - `tcc-g15.spec:42` explicitly configures `uac_admin=True`. Elevated privileges are required for `root\WMI` namespace access. Verified.
2. **Anti-Cheat Non-Invasive Guarantees:**
   - Target matching strictly inspects process basenames via global NT kernel tables (`SystemProcessInformation` via `psutil`). It NEVER opens process handles (`OpenProcess`), reads memory, or inspects command lines. This avoids anti-cheat tripwires (BattlEye, Easy Anti-Cheat, Riot Vanguard).
3. **Supply Chain Promotion Requirement (`psutil`):**
   - `psutil==7.2.2` is currently located in `requirements-dev.txt`. OPP-008 requires `psutil` at runtime. `psutil==7.2.2` must be promoted to `requirements.txt` during Phase 6.

### 3.4 Forensic Privacy Audit Discovery: PII Leak in Diagnostics WMI Dump
- **Empirical Finding:**
  Inspection of `src/GUI/Diagnostics.py:35` revealed that only `('serialnumber', 'uuid', 'pnpdeviceid')` were filtered out.
  An empirical audit of `Win32_ComputerSystem` on the target system revealed unredacted user identifying information:
  - `UserName`: `DESKTOP-83D0CKH\morsh`
  - `PrimaryOwnerName`: `morshedmilton@outlook.com` (user's personal email address)
  - `DNSHostName`: `DESKTOP-83D0CKH`
- **Violation:** This directly contradicts the module docstring ("Never includes usernames..."). Registered as **DEF-006 (P1)** for remediation in Phase 6.

---

## 4. Defect Register (Cycle 006 Status)

| Defect ID | Severity | Category | Description | Status |
|---|---|---|---|---|
| **`DEF-001`** | P0 (Critical) | CI/CD | CI workflow trigger mismatch (`main` branch missing) | **CLOSED** (Remediated in Cycle 001) |
| **`DEF-002`** | P0 (Critical) | Safety | Hardware whitelist missing `G16 7630` and `m15 R7` | **CLOSED** (Remediated in Cycle 001) |
| **`DEF-003`** | P0 (Critical) | Safety | Missing unit test for INV-1 hard fail-safe trip | **CLOSED** (Remediated in Cycle 001) |
| **`DEF-004`** | P1 (High) | Git Hygiene | Tracked debug/log files in repository index | **CLOSED** (Remediated in Cycle 001) |
| **`DEF-005`** | P1 (High) | Supply Chain | Unpinned dependencies and mixed dev/runtime requirements | **CLOSED** (Remediated in Cycle 001) |
| **`DEF-006`** | P1 (High) | Privacy/PII | Diagnostics WMI dump leaks `UserName`, `PrimaryOwnerName`, `DNSHostName` | **OPEN** (Actionable in Phase 6) |
| **`DEF-007`** | P1 (High) | Supply Chain | `psutil==7.2.2` runtime dependency promotion required for OPP-008 | **OPEN** (Actionable in Phase 6) |
| **`DEF-008`** | P0 (Critical) | Safety | OPP-008 switching logic must yield unconditionally to INV-1 fail-safe | **OPEN** (Design constraint for Phase 4/5/6) |
| **`DEF-009`** | P2 (Medium) | Architecture | Cross-thread COM apartment isolation required for process monitor | **OPEN** (Design constraint for Phase 5/6) |

---

## 5. Verification Command Logs & Static Analysis

- **Test Suite Execution:**
  ```powershell
  .venv\Scripts\pytest.exe tests/ -v
  # Result: 42 passed in 6.43s (100% pass rate)
  ```
- **Static Analysis & Linting:**
  ```powershell
  .venv\Scripts\ruff.exe check .
  # Result: All checks passed! (0 errors, 0 warnings)
  ```
- **Hardware & Environment Guard Verification:**
  ```powershell
  .venv\Scripts\python.exe tools/check_env.py
  # Result: ALL CHECKS PASSED (10/10 imports ok, bit packing ok, USTT modes ok, whitelist ok, watchdog ok)
  ```

---

## 6. Gate G2 Sign-Off & Verdict

- **Gate:** G2 (Forensic Hardware & Safety Audit)
- **Verdict:** **CLEAN / PASSED**
- **Authorization:** Safety Invariants INV-1 through INV-6 remain completely intact and verified. Identified safety constraints (DEF-008) and privacy fixes (DEF-006) are scheduled for Phase 4-6 implementation. The repository is cleared to advance to Phase 3 (Prioritization & Scope Selection).
- **Signed:** Forensic Safety Auditor (`teamwork_auditor`), 2026-11-04
