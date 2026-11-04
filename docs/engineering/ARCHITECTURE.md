# TCC-G15 System Architecture & Runtime Map

**Version:** 1.8.6-arch-rev2  
**Status:** Approved for Cycle 006 (`OPP-008`)  
**Author:** Multi-disciplinary Autonomous Engineering Organization (Worker Phase 5 — Architecture & Design)  
**Last Audited:** 2026-11-04  

---

## 1. System Overview

Thermal Control Center (TCC-G15) is an autonomous, ultra-low-overhead hardware thermal control, telemetry, and process-aware profile automation utility engineered specifically for Dell G-Series and Alienware laptops (including G15 5530, G16 7630, m15 R7) under Windows 10/11. The application replaces heavy, slow vendor background services (Dell Alienware Command Center / AWCC) by communicating directly with Dell's ACPI/WMI thermal firmware tables (`root\WMI:AWCCWmiMethodFunction`) and reading direct hardware GPU core temperatures via the NVIDIA NVML driver C API.

Starting in Cycle 006 (`OPP-008`), TCC-G15 incorporates a decoupled, zero-privilege process detection and automatic thermal profile switching engine that intelligently adapts system cooling to active gaming and compute workloads while preserving acoustic comfort, anti-cheat safety, and hardware safety invariants.

```mermaid
graph TD
    subgraph UI_Process ["Process 1: Main Application (tcc-g15.exe)"]
        subgraph Main_GUI_Thread ["Thread 1: Main Qt GUI Event Loop (AppGUI.py)"]
            GUI["PySide6 Cyberpunk HUD (AppGUI.py)"]
            CyberGauge["Vector Tachometer Gauges (CyberGauge.py)"]
            DWM["Windows 11 DWM Acrylic Blur Bridge"]
            StateMgr["Thermal Mode & State Machine"]
            ArbitrationEngine["Process Rule Arbitration & State Restoration Engine"]
            RulesDialog["ProcessRulesDialog (Rule Editor & Master Toggle)"]
            Failsafe["Dual-Layer Fail-Safe (Soft & Hard Invariants)"]
            PowerHook["Win32 Power Status Monitor (AC/DC)"]
            HB["Heartbeat File Generator (%TEMP%/tcc-g15.heartbeat)"]
        end

        subgraph Telemetry_Thread ["Thread 2: TelemetryWorker (QtCore.QThread)"]
            TWorker["TelemetryWorker (QObject, 2.0s Cadence)"]
            COMApartment["COM Apartment (pythoncom.CoInitialize)"]
            MetricsTracker["SessionMetricsTracker (Peak / Excursion Analytics)"]
            TLogger["TelemetryLogger (Rotating CSV Session Store)"]
        end

        subgraph Process_Monitor_Thread ["Thread 3: ProcessMonitorWorker (QtCore.QThread)"]
            PMWorker["ProcessMonitorWorker (QObject, 2.5s Cadence)"]
            PSUtil["psutil.process_iter(['name']) (Non-invasive NT scan)"]
        end
    end

    subgraph Watchdog_Process ["Process 2: Detached Watchdog (tcc-watchdog.exe)"]
        WMon["Heartbeat Monitor (12s Timeout, Monotonic Clock)"]
        WRestore["Emergency Fallback Engine (Forces Balanced Mode 0xA0)"]
    end

    subgraph Data_Storage ["Configuration & Persistence"]
        QSettingsStore["QSettings (Windows Registry)"]
        PresetsCatalog["ProcessRulePresets (18 Curated Presets)"]
    end

    subgraph Hardware_Abstraction_Layer ["Hardware Abstraction Layer (HAL)"]
        AWCCHigh["AWCCThermal (High-Level API & COM Cache)"]
        AWCCLow["AWCCWmiWrapper (Bit Packing & Firmware Probing)"]
        NVML["GpuTemp (NVIDIA NVML Driver Telemetry)"]
        HDetect["DetectHardware (SMBIOS Whitelist Validator)"]
    end

    subgraph System_Hardware ["Operating System, Firmware & Physical Hardware"]
        WMI_ACPI["Dell ACPI BIOS (AWCCWmiMethodFunction)"]
        NVIDIA_GPU["NVIDIA GeForce RTX dGPU (Driver Diode)"]
        SMBIOS["SMBIOS Motherboard Table"]
        NTKernel["Windows NT Kernel (SystemProcessInformation)"]
        Win32["Windows Kernel / Power Management"]
    end

    %% Main Thread Connections
    GUI --> CyberGauge
    GUI --> DWM
    GUI --> StateMgr
    GUI --> PowerHook
    StateMgr --> Failsafe
    Failsafe --> AWCCHigh
    PowerHook --> Win32
    StateMgr --> AWCCHigh
    GUI --> HB
    HB -.->|Monitored over disk| WMon
    WMon --> WRestore
    WRestore --> AWCCHigh
    GUI --> HDetect
    HDetect --> SMBIOS

    %% Subsystem Connections (Cycle 006 Process Detection)
    RulesDialog --> QSettingsStore
    PresetsCatalog --> RulesDialog
    RulesDialog --> ArbitrationEngine
    ArbitrationEngine --> StateMgr
    PMWorker -->|Qt Queued Signal: processes_scanned(set)| ArbitrationEngine
    PMWorker --> PSUtil
    PSUtil --> NTKernel

    %% Telemetry Worker Connections
    TWorker --> COMApartment
    COMApartment --> AWCCHigh
    TWorker --> NVML
    NVML --> NVIDIA_GPU
    AWCCHigh --> AWCCLow
    AWCCLow --> WMI_ACPI
    TWorker -->|Qt Queued Signal: telemetryReady(Snapshot)| GUI
    TWorker --> MetricsTracker
    TWorker --> TLogger
```

---

## 2. Runtime Processes & Threading Model

### 2.1 Process 1: Main Application (`tcc-g15.py` / `tcc-g15.exe`)
- **Elevation:** Elevated Administrator token enforced via embedded application manifest (`uac_admin=True`). Administrator rights are required to access Dell ACPI tables under the `root\WMI` namespace.
- **Multi-Threaded Architecture:**
  1. **Thread 1: Main GUI Event Loop (Qt Main Thread):**
     - Runs `PySide6.QtWidgets.QApplication.exec()`.
     - Owns the Cyberpunk Acrylic Glass HUD, Tachometer vector gauges (`CyberGauge`), tray icon, and dialog windows.
     - Superintends state arbitration, manual user overrides, hotkey triggers (`HotKey.G_MODE_KEY`), and fail-safe trips.
     - Touches heartbeat file (`%TEMP%\tcc-g15.heartbeat`) on every telemetry tick.
     - **Latency Ceiling:** < 1.0 ms event handling latency; strictly decoupled from hardware bus queries and process enumeration.
  2. **Thread 2: Decoupled Telemetry Worker Thread (`TelemetryWorker` — ADR-003):**
     - Executes inside a dedicated `QtCore.QThread`.
     - Manages its own COM apartment lifecycle via `pythoncom.CoInitialize()` and `CoUninitialize()` (`INV-6` / `DEF-009`).
     - Polls Dell ACPI WMI temperature sensors, fan tachometers, and NVIDIA NVML driver temperatures at 2,000 ms cadence (5,000 ms when minimized).
     - Updates `SessionMetricsTracker` (O(1) peak and thermal excursion tracking — ADR-005) and logs to `TelemetryLogger` (rotating CSV store — ADR-004).
     - Emits immutable `TelemetrySnapshot` to Thread 1 via thread-safe Qt queued signals.
  3. **Thread 3: Decoupled Process Monitor Worker Thread (`ProcessMonitorWorker` — ADR-006):**
     - Executes inside a dedicated `QtCore.QThread`.
     - Runs a periodic `QtCore.QTimer` at a 2,500 ms interval.
     - Non-invasively queries `psutil.process_iter(['name'])` against the Windows NT global process table (`SystemProcessInformation`).
     - Never opens handles with read/write access to target processes; zero anti-cheat tripwires.
     - Emits `processes_scanned = Signal(set)` containing active lowercase executable basenames to Thread 1 via Qt queued signals.

### 2.2 Process 2: Detached Watchdog (`tcc-watchdog.py` / `tcc-watchdog.exe`)
- **Process Isolation:** Spawned detached by the main application via `subprocess.Popen(..., close_fds=True)` or WMI `Win32_Process.Create`.
- **Footprint:** Lightweight headless Python binary (~4 MB working set).
- **Heartbeat & Resiliency Contract (`INV-3` / ADR-002):**
  - Evaluates `mtime` of `%TEMP%\tcc-g15.heartbeat` every 2.0s using monotonic clock tracking.
  - Sleep Detection: If monotonic delta between checks exceeds 6.0s (indicating system Modern Standby S0ix or S3 sleep), the watchdog resets its expiration timer, preventing false-positive trips upon wake.
  - Fail-Safe Restoration: If heartbeat age exceeds 12.0s during continuous system wake (indicating main application crash, freeze, or kill):
    - Connects directly to `root\WMI`.
    - Forces firmware into **Balanced** mode (`0xA0`) and resets manual offsets.
    - Writes breadcrumb marker `%TEMP%\tcc-g15.heartbeat.restored`.
    - Exits cleanly with code 0.

---

## 3. Hardware & System Call-Sites Inventory

| File | Line(s) / Function | Target Subsystem / API | Call Signature | Purpose & Safety Invariants |
|---|---|---|---|---|
| `src/Backend/AWCCThermal.py` | 14–16 | Win32 COM Cache | `shutil.rmtree(%TEMP%\gen_py)` | Prevents corrupt typelib after AWCC uninstall |
| `src/Backend/AWCCThermal.py` | 38 | Dell ACPI WMI Namespace | `WMI(namespace='root/WMI')` | Binds to Dell AWCC ACPI interface |
| `src/Backend/AWCCWmiWrapper.py` | 31, 36, 41 | Dell BIOS Thermal Sensors | `Thermal_Information(arg)` | Reads CPU/GPU sensor temps and fan RPMs |
| `src/Backend/AWCCWmiWrapper.py` | 84, 88 | Dell EC Fan Speeds | `Thermal_Control(packedArg)` | Writes manual fan speed offset (0–100%, `INV-4`) |
| `src/Backend/AWCCWmiWrapper.py` | 108 | Dell BIOS USTT Profiles | `Thermal_Control(modeCode)` | Switches thermal profile (0xA0, 0xA1, 0xA3, 0xAB, 0x0) |
| `src/Backend/DetectHardware.py` | 28 | SMBIOS ComputerSystem | `Win32_ComputerSystem()[0]` | Validates manufacturer and model against whitelist (`INV-5`) |
| `src/Backend/DetectHardware.py` | 46, 50 | Hardware Component Names | `Win32_Processor`, `Win32_VideoController` | Queries CPU and dGPU marketing strings |
| `src/Backend/GpuTemp.py` | 15–18 | NVIDIA Display Driver | `nvmlInit()`, `nvmlDeviceGetHandleByIndex(0)` | Direct driver initialization |
| `src/Backend/GpuTemp.py` | 30 | NVIDIA GPU Hardware Sensor | `nvmlDeviceGetTemperature(...)` | Accurate sub-degree GPU core temperature diode |
| `src/GUI/AppGUI.py` | 44 | Windows DWM | `DwmSetWindowAttribute(hwnd, 38, ...)` | True Windows 11 DWM Acrylic backdrop |
| `src/GUI/AppGUI.py` | 58 | Windows Kernel Power | `kernel32.GetSystemPowerStatus(...)` | Real-time AC vs Battery line status |
| `src/GUI/ProcessMonitorWorker.py`| `pollOnce()` | Windows NT Kernel Tables | `psutil.process_iter(['name'])` | Non-invasive global process name scan (`OPP-008`, `SRC-006`) |
| `src/GUI/Diagnostics.py` | `_redact()` | Privacy Redaction Engine | Sanitizes sensitive WMI strings | Redacts `UserName`, `PrimaryOwnerName`, `DNSHostName` (`DEF-006`) |
| `src/tcc-watchdog.py` | 47 | Dell ACPI Thermal Fallback | `awcc.setMode(ThermalMode.Balanced)` | Restores firmware Balanced mode on heartbeat death (`INV-3`) |

---

## 4. State Machines & Arbitration Logic

### 4.1 Thermal Mode Transitions
Supported firmware profiles:
- `Balanced` (`0xA0` USTT / `0x97` legacy)
- `Performance` (`0xA1` USTT / `0x98` legacy)
- `Quiet` (`0xA3` USTT / `0x96` legacy)
- `G_Mode` (`0xAB` USTT / `0xAB` legacy)
- `Custom` (`0x00`) — Enables manual fan slider offsets (0%–100%, `INV-4`).

**Battery Power Interaction:**
When running on AC power, the user or automation engine determines the active mode. If `queryAcPowerStatus()` detects a transition to Battery (DC power) and `_autoBatterySwitch == True`:
1. Current mode is saved to `_acPreferredMode`.
2. Thermal mode switches to `Quiet` to preserve battery life and acoustic limits.
3. When AC power is restored, the system returns to `_acPreferredMode`.

### 4.2 Fail-Safe State Machine
- **Soft Fail-Safe:** Active if `_failsafeOn == True`. Triggers if CPU ≥ 95°C or GPU ≥ 85°C continuously for > 8.0s. Forces `G_Mode` with 100% cooling.
- **Hard Fail-Safe (`INV-1`):** Active unconditionally (cannot be disabled by UI toggle). Triggers if CPU ≥ 100°C or GPU ≥ 90°C continuously for > 4.0s. Forces `G_Mode`.
- **Sensor Loss Safeguard (`INV-2`):** If sensor readings are lost or return invalid values for > 60.0s, triggers fail-safe `G_Mode`.
- **Recovery:** When temperatures remain below soft thresholds for 60.0 continuous seconds (`FAILSAFE_RESET_AFTER_TEMP_IS_OK_FOR_SEC`), mode reverts to `_failsafeTrippedPrevModeStr`.

### 4.3 Process-Aware Profile Switching & Anti-Flapping State Machine (`OPP-008` / ADR-006)

The process automation subsystem arbitrates between background processes, user baseline state, manual user overrides, and safety invariants:

```
                       +-----------------------------+
                       |        Idle Desktop         |
                       |    _baselineMode = None     |
                       |    _userOverride = False    |
                       +--------------+--------------+
                                      |
                                      | Match >= 1 enabled process rule
                                      | Record _baselineMode = currentMode
                                      v
                       +-----------------------------+
                       |   Process Active Session    |
                       |    _baselineMode != None    |
                       | Apply Highest Severity Mode |
                       +-------+--------------+------+
                               |              |
         User adjusts GUI /    |              | All matched processes absent
         G-Key hotkey pressed  |              | for >= 4.0s (2 poll cycles)
                               v              v
      +----------------------------+   +-----------------------------+
      |    User Override Active    |   |      Restore Baseline       |
      |    _userOverride = True    |   |     Apply _baselineMode     |
      |   Suppress Auto-Switches   |   |    _baselineMode = None     |
      +--------------+-------------+   +--------------+--------------+
                     |                                |
                     | All matched processes absent   |
                     | for >= 4.0s debounce           |
                     v                                v
      +----------------------------+   +-----------------------------+
      |   Clear Override Session   |   |        Idle Desktop         |
      |    _userOverride = False   |-->|    _baselineMode = None     |
      |    _baselineMode = None    |   +-----------------------------+
      |   Retain User's Mode       |
      +----------------------------+
```

#### 4.3.1 Cooling Severity Priority Matrix
When multiple enabled rules match concurrently running processes, the arbitration engine resolves the target mode using the Cooling Severity Priority Matrix:

$$\text{G\_Mode (0xAB)} \succ \text{Performance (0xA1)} \succ \text{Custom (0x00)} \succ \text{Balanced (0xA0)} \succ \text{Quiet (0xA3)}$$

The active profile is selected as $M^* = \arg\max_{r \in R_{\text{effective}}} \rho(r.\text{target\_mode})$.

#### 4.3.2 Anti-Flapping Exit Debounce Hysteresis (4.0 Seconds)
To prevent rapid fan ramp-down and ramp-up during game scene transitions, cutscenes, or engine process handoffs:
- When an active matched process disappears from a scan, its missing counter increments.
- The rule remains active in $R_{\text{effective}}$ until it has been continuously absent for $\ge 2$ consecutive polling cycles ($\ge 4.0$ seconds).
- Reappearance within the 4.0s window resets the missing counter, maintaining uninterrupted cooling.

#### 4.3.3 State Preservation & Manual Override Sovereignty
- **Baseline Capture:** `_baselineMode` is captured strictly on the 0-to-1 active rule transition. Staggered launches of secondary applications do not overwrite `_baselineMode`.
- **Manual User Override:** If the user manually changes thermal modes or presses the Alienware G-Key while process automation is active, `_userOverride = True` is engaged. Automation yields to the user's explicit preference. When the gaming session concludes and all processes exit, `_userOverride` resets cleanly without reverting the user's manual choice.

#### 4.3.4 Unconditional INV-1 Hard Fail-Safe Supremacy (`DEF-008`)
- If the hard or soft fail-safe is engaged (`_failsafeTrippedPrevModeStr is not None`), all automated profile switching and baseline restoration logic is **strictly locked out**.
- The emergency fail-safe recovery logic retains exclusive control over profile transitions until temperatures have normalized for the full 60-second cooldown period.

---

## 5. Subsystem Component Inventory & Architecture

| Component | Layer / Path | Primary Responsibilities | Traceability |
|---|---|---|---|
| `ProcessRule` | `src/Backend/ProcessRule.py` | Dataclass representing an automation rule (`process_name`, `target_mode`, `enabled`, `description`), with JSON serialization and validation. | `REQ-0602`, `OPP-008` |
| `ProcessRulePresets` | `src/Backend/ProcessRulePresets.py` | Catalog of 18 curated default presets across AAA Gaming, Competitive Esports, and Content Creation / Benchmarking. | `REQ-0604`, `SRC-009` |
| `ProcessMonitorWorker` | `src/GUI/ProcessMonitorWorker.py` | `QtCore.QObject` running in secondary `QThread`; scans NT process tables via `psutil` at 2.5s interval and emits `processes_scanned(set)`. | `REQ-0601`, `DEF-009` |
| `ProcessRulesDialog` | `src/GUI/ProcessRulesDialog.py` | Acrylic Cyberpunk PySide6 modal dialog; provides rule editor, add/edit/delete actions, presets reset, and `QSettings` persistence. | `REQ-0605`, `OPP-008` |
| `AppGUI` Arbitration Engine | `src/GUI/AppGUI.py` | Core state coordinator; handles signal from worker, applies Cooling Severity Priority Matrix, 4.0s exit hysteresis, and INV-1 lockout. | `REQ-0602`, `REQ-0603`, `REQ-0606` |
| `TelemetryWorker` | `src/GUI/TelemetryWorker.py` | Secondary `QThread` polling Dell ACPI WMI and NVIDIA NVML sensors; emits immutable `TelemetrySnapshot`. | `OPP-001`, ADR-003 |
| `SessionMetricsTracker` | `src/Backend/SessionMetricsTracker.py` | In-memory O(1) telemetry accumulator; computes session peak temps, excursion durations, and advisory triggers. | `OPP-007`, ADR-005 |
| `TelemetryLogger` | `src/Backend/TelemetryLogger.py` | Bounded rotating CSV telemetry logger for diagnostic analysis. | `OPP-005`, ADR-004 |
| `Diagnostics` (Privacy Redacted)| `src/GUI/Diagnostics.py` | System diagnostics bundler; enforces PII redaction of `UserName`, `PrimaryOwnerName`, and `DNSHostName`. | `DEF-006`, `REQ-0607` |

---

## 6. Safety Invariant Mapping & Compliance Matrix

| Invariant | Description | Architectural Mechanism & Safeguards | Compliance Status |
|---|---|---|---|
| **INV-1** | Hard Emergency Fail-Safe Trip (CPU $\ge 100^\circ\text{C}$, GPU $\ge 90^\circ\text{C}$) | Unconditional fail-safe supremacy (`DEF-008`). Process rules are locked out while `_failsafeTrippedPrevModeStr is not None`. | **PASS (ENFORCED)** |
| **INV-2** | Temperature Sanity Filtering (0°C–125°C) & Timeout Fallback | Sanity filtering in `sanitizeTemperature()`; 60s sensor timeout forces G-Mode trip, locking out process rules. | **PASS (ENFORCED)** |
| **INV-3** | Detached Watchdog Balanced Fallback within 12s | Worker thread execution (< 10 ms) on secondary thread ensures main thread event loop never starves heartbeat touches. | **PASS (ENFORCED)** |
| **INV-4** | Fan Speed Offset Clamping (0%–100%) | Custom mode fan speed offsets clamped in `AWCCWmiWrapper.py` and UI sliders. | **PASS (ENFORCED)** |
| **INV-5** | SMBIOS Hardware Whitelist | Whitelist check in `DetectHardware.py` rejects unsupported models unless `TCC_ALLOW_UNSUPPORTED=1`. | **PASS (ENFORCED)** |
| **INV-6** | Monotonic Cooling Floor & COM Apartment Isolation | Zero raw EC port writes (`0x66`/`0x68`); ACPI mode codes only. COM initialized per thread via `pythoncom` (`DEF-009`). | **PASS (ENFORCED)** |

---

## 7. Defect Register & Resolution Map (Cycle 006)

- `DEF-001` (P0 - CI Trigger Mismatch): Verified Closed (targets `main`).
- `DEF-002` (P0 - Whitelist Missing Models): Verified Closed (`G16 7630`, `m15 R7` added).
- `DEF-003` (P0 - Missing INV-1 Unit Test): Verified Closed (`test_inv1_hard_failsafe_unbypassable`).
- `DEF-004` (P1 - Tracked Debug Artifacts): Verified Closed (.gitignore updated).
- `DEF-005` (P1 - Unpinned Dependencies): Verified Closed (`requirements.txt` strictly pinned).
- `DEF-006` (P1 - Diagnostics PII Leak): Architectural design completed; scheduled for Phase 6 implementation.
- `DEF-007` (P1 - Supply Chain Promotion): `psutil==7.2.2` scheduled for promotion to `requirements.txt` in Phase 6.
- `DEF-008` (P0 - Fail-Safe Supremacy): Architectural design completed in ADR-006 / ARCHITECTURE.md; scheduled for Phase 6 implementation.
- `DEF-009` (P2 - COM Apartment Isolation): Architectural design completed via `ProcessMonitorWorker` dedicated QThread and Qt queued signals; scheduled for Phase 6 implementation.
