# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- **Apple Liquid Glass UI/UX Overhaul:** Re-engineered the interface inspired by Linear and Apple Notes. Integrated Windows 11 DWM dark title bar and Acrylic frosted glass backdrop (`#0e1015`, specular top highlights), macOS/Linear segmented pill selector for thermal modes, glowing jewel LED indicator for fail-safe status, and sleek rounded 8px glass pill gauges.
- **Ultra-Compact UI Restoration:** Restored the sleek, compact two-row window layout from original upstream, eliminating extra rows and oversized blank margins while accommodating all 5 modes and fail-safe controls on a single row.
- **Removed Redundant Secondary Labels:** Cut taglines, helper text, and secondary labels (e.g. removed redundant "Fan Speed" text; fan slider spans full width seamlessly).
- **Zero UI Wakeup Optimization:** Removed continuous 30ms animation timer to ensure minimal CPU load (<0.20% CPU idle) and reduced wakeups (from 21.5/s down to ~10/s).
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
