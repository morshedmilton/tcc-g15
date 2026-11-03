# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.4] - 2026-11-04

### Added
- **Bounded Session Telemetry Logging (`OPP-006` / ADR-004):** Comprehensive session hardware telemetry logging in standard RFC 4180 CSV format (`%LOCALAPPDATA%\tcc-g15\telemetry\session_<YYYYMMDD_HHMMSS>.csv`). Logs timestamps, CPU/GPU temperatures, fan RPMs, thermal modes, and AC power status.
- **Strict Bounded Retention & Size Guard:** Automatic size capping (10 MB per file) and bounded rotation (retaining maximum 5 recent sessions) to guarantee zero unbounded disk accumulation on user systems.
- **System Tray Controls & Persistence:** Added "Session telemetry logging" toggle and "Open logs directory" menu actions with preference persistence (`app/telemetry_logging`).
- **Diagnostics Bug Report Integration:** Automatic inclusion of the most recent session `telemetry.csv` inside `bugreport-<stamp>.zip` for rapid hardware issue triage.
- **Unit Test Coverage:** 6 unit tests in `tests/test_telemetry_logger.py` validating CSV formatting, size caps, pruning, disabled state, and zip bundle integration.

---

## [1.8.3] - 2026-11-04

### Added
- **Decoupled Background Telemetry Engine (`OPP-001` / ADR-003):** Telemetry queries (Dell ACPI WMI and NVIDIA NVML driver reads) now run in a dedicated `QtCore.QThread` via `TelemetryWorker`, completely decoupling slow COM/driver queries from the Qt GUI Main Thread and eliminating UI micro-stutters during heavy system load.
- **Strongly-Typed Immutable Telemetry Snapshot (`OPP-005`):** Introduced frozen `TelemetrySnapshot` data transfer object for thread-safe cross-apartment sensor communication.
- **Comprehensive Telemetry Worker Unit Tests:** Added 6 new automated unit tests in `tests/test_telemetry_worker.py` covering worker polling, signal dispatch, NVML fallback to WMI, and clean QThread lifecycle teardown.

---

## [1.8.2] - 2026-11-04

### Added
- **Machine-Readable CycloneDX SBOM:** Automated generation of `tcc-g15-sbom.json` (CycloneDX v1.6) in the build and CI pipelines, providing cryptographic supply-chain verification.
- **Watchdog Auto-Resurrection:** GUI now verifies the health of the detached watchdog process during periodic background ticks and automatically restarts it if it was terminated, keeping hardware protected at all times.

### Fixed
- **Watchdog Sleep / Standby Resilience:** Watchdog now tracks monotonic loop elapsed time (`time.monotonic()`) across sleep intervals to detect operating system suspend (lid close / modern standby / S3 sleep). On resume, it grants a grace window instead of prematurely triggering a false emergency mode restore and exiting.
- **Thermal Mode Application Retry:** Added transient retry logic in `AWCCWmiWrapper.ApplyThermalMode` to handle brief WMI ACPI bus contention before concluding a mode is unsupported.

---

## [1.8.1] - 2026-11-04

### Fixed
- **CI Workflow Default Branch:** Fixed GitHub Actions CI trigger in `.github/workflows/ci.yml` to run on `main` and PRs targeting `main` (resolving issue where CI never triggered on default branch).
- **Hardware Whitelist Expansion:** Added missing `Dell G16 7630` and `Alienware m15 R7` to `SUPPORTED_MODELS` whitelist, reconciling code with documentation claims.
- **Safety Invariant INV-1 Test:** Added automated regression test in `tests/test_safety_and_failsafe.py` verifying that hard emergency trips to G-Mode occur even if soft fail-safe is disabled by user.
- **Repository Cleanliness:** Untracked 34 runtime debug logs, PID files, and temporary artifacts from git index, with comprehensive `.gitignore` rules.
- **Dependency Pinning:** Pinned exact runtime dependency versions in `requirements.txt` and separated development/testing tooling into `requirements-dev.txt`.

---

## [1.8.0] - 2026-11-03

### Added
- **Full 5 Thermal Profiles on Dell G15 5530:** Added hardware-verified `Quiet` (USTT 0xA3) and `Performance` (USTT 0xA1) profiles alongside `Balanced` (USTT 0xA0), `G-Mode` (0xAB), and `Custom` (0x0).
- **Smart Power Automation:** Detects AC vs Battery status via Win32 API. Automatically shifts to `Quiet` mode on battery to eliminate excessive fan noise and maximize battery life, restoring preferred AC profile when plugged back in.
- **Hardware Watchdog:** Standalone watchdog process (`tcc-watchdog.exe`) launched detached via WMI. Monitors heartbeat file and restores `Balanced` mode if the main application crashes or is terminated (`taskkill /T`, Task Manager).
- **Direct NVIDIA NVML GPU Temperature:** Primary GPU temperature reading sourced via NVML directly from the driver, eliminating the upstream Dell WMI 2–3°C idle reading bug. Dell WMI sensor 6 kept as fallback.
- **Hardware Whitelist:** Verifies laptop SMBIOS model at launch against known compatible Dell G15 systems (with `TCC_ALLOW_UNSUPPORTED=1` override).
- **One-Click Bug Report Diagnostics:** Bundles system specs, WMI survey, and application logs into a privacy-redacted zip and pre-populates GitHub issue.
- **Pytest Unit Test Suite:** 14 automated tests with mocked WMI abstraction layer for CI.
- **GitHub Actions CI Workflow:** Automated linting, testing, and artifact build pipeline.

### Changed
- **Cyberpunk HUD & DWM Acrylic Translucency Overhaul:** Complete visual transformation into a futuristic gaming rig thermal HUD. Incorporates custom `CyberGauge` widgets featuring 25° skewed bar geometry, diagonal technical hatch dividers, and dynamic gradient shifting (Toxic Green `#00FF66` -> Cyber Yellow `#FCEE0A` -> Hazard Crimson `#FF003C`).
- **True Desktop Acrylic Glass Effect:** Enabled `Qt.WA_TranslucentBackground` paired with Windows 11 DWM Acrylic (`DWMWA_SYSTEMBACKDROP_TYPE = 3`) and semi-transparent cyber-dark slate backdrops (`rgba(10, 12, 18, 0.82)`), delivering true desktop blur and frosted glass bleed-through without opaque occlusion.
- **Cyberpunk Tactical Control Deck:** Redesigned thermal profile buttons with angled cyber borders, high-contrast neon accents, active overdrive states (`G-MODE // OVRD` in neon crimson), and tactical `▲ SAFEGUARD` beacon.
- **Ultra-Compact UI Layout:** Restored the sleek, compact two-row window layout from original upstream, eliminating extra rows and oversized blank margins while accommodating all 5 modes and fail-safe controls on a single row.
- **Zero UI Wakeup Optimization:** Pure vector `QPainter` rendering with zero continuous animation timers, preserving ultra-low CPU consumption (<0.20% CPU idle) and minimal thread wakeups.
- **Fail-Safe Robustness:** Reinforced fail-safe logic with an 8-second debounce to ignore transient spikes, plus an un-bypassable hard safety threshold at 100°C CPU / 90°C GPU.

---

## [1.7.0] - 2026-11-02

### Fixed
- Fixed Balanced mode silently falling back to Custom mode (bool-as-int bug).
- Fixed G-mode persisting across reboots when saved in settings.
- Added `_saneTemp()` guard to filter out implausible readings (< 5°C or > 120°C).
- Added automatic clearing of stale win32com COM cache (`%TEMP%/gen_py`) and WMI handshake retry.
- Filtered unsupported -2 return codes from Dell WMI for fan RPM percent.

---

## [1.6.4] - 2025-01-18 (Upstream)
- Original release by AlexIII.
