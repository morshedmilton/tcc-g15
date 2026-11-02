# RISKS.md — tcc-g15 G15 5530 Fork

**Updated:** 2026-11-03  
**Review cadence:** After each phase + before each hardware-write test

---

## Risk Register

| ID | Risk | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|---|
| R-01 | **Fan control sets unsafe speed** (below BIOS floor, causing overheating) | Medium | Critical (hardware damage) | Hard fail-safe: temp threshold + debounce → max cooling/G-mode; UI cannot disable; watchdog restores defaults on crash/kill/sleep | Designed (batch 1), not yet tested on hardware |
| R-02 | **WMI call hangs / crashes the app** (Dell WMI provider bugs) | Medium | High (UI freeze, lost control) | Async WMI calls with timeout; watchdog process monitors GUI heartbeat; separate elevated service isolates crash | Architecture decision pending (ADR-004) |
| R-03 | **G-mode switch causes system-wide freeze** (known Dell firmware issue, upstream #21) | High (observed on 5515/5520) | Medium (UX, potential data loss) | Debounced fail-safe; disable fail-safe while gaming (UI option); document as known limitation; measure on 5530 in Phase 2 | Measuring in Phase 2 |
| R-04 | **Bogus GPU temp (2–3°C) triggers false fail-safe or hides real overheat** | High (upstream #9, #85, 5530 owner report) | High | `_saneTemp()` guard (5–120°C) + 60s grace before silent sensor trips fail-safe; implemented in batch 1 | Implemented (7ac9d87), needs hardware validation |
| R-05 | **AWCC uninstall leaves stale COM cache breaking WMI** (upstream #64) | Medium | High (app won't start) | `clearStaleComCache()` on import failure + retry; implemented | Implemented (7ac9d87) |
| R-06 | **Boot-time WMI race** (AWCC service not ready, upstream #90) | Medium | Medium | Retry with backoff (5×1.5s) + cache clear; implemented | Implemented (7ac9d87) |
| R-07 | **Autorun via Task Scheduler unreliable** (upstream #49, #13) | High | Low-Medium | Replace with Startup folder / registry Run key + verification; planned Batch 2 | Planned |
| R-08 | **BIOS update changes WMI interface / sensor map** | Low | High | SMBIOS model + BIOS version check at startup; refuse to run on unknown config; document 5530/BIOS 1.36.0 as validated | Designed, not implemented |
| R-09 | **Python/PySide6 resource usage too high** (idle CPU%, RAM, wakeups) | Unknown | Medium | Phase 2 baseline measurement; if exceeds thresholds → ADR-003 triggers rewrite | Phase 2 in progress |
| R-10 | **Upstream goes completely dormant / hostile fork** | Low | Low | We own the fork; GPL-3.0 allows independent continuation; community can migrate | Accepted |
| R-11 | **Legal: Dell/Alienware trademark in product name** | Low | Critical | Product name: "Thermal Control Center for Dell G15 (unofficial fork)"; no Dell/Alienware logos; clean-room WMI derivation only | Enforced in README |
| R-12 | **Contributor submits proprietary Dell/AWCC code** | Low | Critical | CONTRIBUTING.md forbids it; CI secret scan; PR template requires clean-room attestation | Phase 4 |
| R-13 | **Windows Update breaks WMI namespace / permissions** | Low | High | Test on Windows Insider builds if possible; document recovery (re-enable WMI, restore point) | Watching |
| R-14 | **False positive antivirus flag on unsigned PyInstaller exe** | Medium | Medium | Code-sign cert (later); VirusTotal scan in CI; document in README | Phase 6 |
| R-15 | **Sleep/resume breaks WMI handle / fan state** | Medium | High | Watchdog detects resume → re-init WMI → restore default mode; test in Phase 6 | Phase 6 |

---

## Hardware-Safety Checklist (Pre-Flight for Every Hardware Test)

- [ ] Windows restore point created
- [ ] Live temperature monitoring visible (HWInfo / Task Manager / second terminal)
- [ ] Auto-abort script ready (temp > 95°C CPU or > 88°C GPU → kill app, restore Balanced)
- [ ] Test runs elevated (admin) but time-boxed (max 30 min per workload)
- [ ] Fan behavior logged to CSV (RPM, mode, temp, timestamp)
- [ ] Rollback plan: `schtasks /delete /tn "TCC_G15" /f` + delete startup shortcut

---

## Risk Review Log

| Date | Phase | Reviewer | Changes |
|---|---|---|---|
| 2026-11-02 | 0–1 | Self | Initial register created |
| 2026-11-03 | 2 | Self | R-04, R-05, R-06 mitigated in batch 1 (7ac9d87) |

---

## Next Risk Actions

1. **Phase 2 baseline** → quantify R-03 (freeze frequency), R-09 (resource usage), validate R-04 on 5530
2. **Gate 1** → decide ADR-003 (stack) and ADR-004 (privilege split) based on data
3. **Before first hardware-write test** → create restore point, run through Hardware-Safety Checklist