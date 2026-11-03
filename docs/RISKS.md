# RISKS.md — tcc-g15 G15 5530 Fork

**Updated:** 2026-11-03  
**Review cadence:** After each phase + before each hardware-write test

---

## Risk Register

| ID | Risk | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|---|
| R-01 | **Fan control sets unsafe speed** (below BIOS floor, causing overheating) | Low | Critical (hardware damage) | Hard fail-safe (8s debounce for transient spikes + hard un-bypassable threshold at 100°C CPU / 90°C GPU); watchdog restores Balanced defaults on crash/kill. | ✅ Mitigated & Verified |
| R-02 | **WMI call hangs / crashes the app** (Dell WMI provider bugs) | Low | High (UI freeze, lost control) | Watchdog launched detached via WMI monitors heartbeat; restores Balanced mode if app freezes >12s. | ✅ Mitigated & Verified |
| R-03 | **G-mode switch causes system-wide freeze** (observed on older 5515/5520) | Low | Medium (UX, potential data loss) | Verified on G15 5530 (BIOS 1.36.0): G-mode switches cleanly with 0 system stutter. | ✅ Verified on 5530 |
| R-04 | **Bogus GPU temp (2–3°C) triggers false fail-safe or hides real overheat** | High (upstream #9) | High | Primary GPU temperature sourced via direct NVIDIA NVML driver; `_saneTemp()` guard (5–120°C) filters anomalies. | ✅ Mitigated & Verified |
| R-05 | **AWCC uninstall leaves stale COM cache breaking WMI** (upstream #64) | Medium | High (app won't start) | `clearStaleComCache()` clears `%TEMP%/gen_py` on import failure + retry. | ✅ Mitigated (7ac9d87) |
| R-06 | **Boot-time WMI race** (AWCC service not ready, upstream #90) | Medium | Medium | Retry with backoff (5×1.5s) + cache clear. | ✅ Mitigated (7ac9d87) |
| R-07 | **Autorun via Task Scheduler unreliable** (upstream #49, #13) | Low | Low-Medium | Scheduled task XML with `HighestAvailable` runlevel and verification. | ✅ Mitigated |
| R-08 | **BIOS update changes WMI interface / sensor map** | Low | High | SMBIOS model whitelist verified at startup (`DetectHardware.py`). Refuses unknown systems without explicit override. | ✅ Mitigated |
| R-09 | **Python/PySide6 resource usage too high** (idle CPU%, RAM, wakeups) | Low | Medium | Measured: **0.19% CPU**, **27.6 MB RAM**, **10.5 wakeups/s** (visible), **~2 wakeups/s** (tray). Exceeds targets. | ✅ Resolved (ADR-003) |
| R-10 | **Upstream goes completely dormant / hostile fork** | Low | Low | We own the fork under GPL-3.0; independent release cycle active. | ✅ Accepted |
| R-11 | **Legal: Dell/Alienware trademark in product name** | Low | Critical | Product name: "Thermal Control Center for Dell G15 (unofficial fork)"; no proprietary logos; clean-room WMI derivation. | ✅ Enforced |
| R-12 | **Contributor submits proprietary Dell/AWCC code** | Low | Critical | CONTRIBUTING.md forbids proprietary code; PR template requires clean-room attestation; CI scan. | ✅ Enforced |
| R-13 | **Windows Update breaks WMI namespace / permissions** | Low | High | Tested on Windows 11 Pro build 26300; verified functional. | ✅ Watching |
| R-14 | **False positive antivirus flag on unsigned PyInstaller exe** | Medium | Medium | Clean build with PyInstaller + Inno Setup installer; open-source code verification. | ✅ Mitigated |
| R-15 | **Sleep/resume breaks WMI handle / fan state** | Medium | High | Watchdog and heartbeat logic detects stale heartbeat and re-applies balanced defaults. | ✅ Mitigated |
| R-16 | **No Windows restore point available** | Low | Low | Writes are transient thermal-mode state wiped by reboot; `restore_default_mode.py` provides instant recovery. | ✅ Accepted gap |
