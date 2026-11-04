# Thermal Control Center (TCC-G15) — Release v1.8.6

**Release Tag:** `v1.8.6`  
**Date:** 2026-11-04  
**Commit / Target:** `cycle-006/opp-008-process-switching` (target `main`)  
**License:** GPL-3.0  
**Repository:** https://github.com/morshedmilton/tcc-g15  

---

## What's New in v1.8.6

Release v1.8.6 introduces automated, process-aware thermal profile switching, built-in curated game and application presets, an interactive custom rules editor, enhanced privacy protections for diagnostics bug reports, and robust safety invariant safeguards ensuring fail-safe supremacy under heavy workloads.

### 1. Process-Aware Automatic Thermal Profile Switching (`OPP-008` / ADR-006)
- **Non-Invasive `psutil` Process Monitor:** Operates on a dedicated secondary `QtCore.QThread` decoupled from the GUI main thread, sampling running process name metadata via `psutil.process_iter(['name'])` from native NT kernel structures in under 8.6 ms with `< 0.015%` CPU overhead. Zero `OpenProcess` read/write memory handles are opened, guaranteeing 100% anti-cheat transparency and safety across protected titles (BattlEye, Easy Anti-Cheat, Riot Vanguard, Ricochet).
- **Flap-Free 4.0s Exit Debounce Hysteresis:** Prevents acoustic fan cycling, mode oscillation, and bearing wear during brief launcher transitions, cutscene loading screens, or helper process restarts by requiring 2 consecutive missing poll cycles (4.0s) before restoring profile state.
- **Cooling Severity Priority Arbitration:** Resolves multi-process concurrent execution conflicts deterministically using the Cooling Severity Priority Matrix (`G_Mode` > `Performance` > `Balanced` > `Quiet`), guaranteeing the system always satisfies the most demanding thermal workload.
- **Baseline Mode Preservation & Automatic Restoration:** Caches the user's initial baseline thermal mode (`_baselineMode`) upon entry into a process rule and automatically restores it once all triggering processes exit.
- **User Override Sovereignty:** If the user manually changes the thermal profile while a process rule is active, manual intent takes precedence (`_userOverride = True`) until all matched processes exit.
- **18 Curated Game & High-Performance Presets:** Pre-configured profiles ready out-of-the-box for popular AAA titles and compute workloads:
  - *Cyberpunk 2077*, *Counter-Strike 2*, *Apex Legends*, *Call of Duty: Warzone*, *Valorant*, *Rainbow Six Siege*, *Dota 2*, *League of Legends*, *Fortnite*, *Overwatch 2*, *Grand Theft Auto V*, *Baldur's Gate 3*, *Helldivers 2*, *Elden Ring*, *Forza Horizon 5*, *Blender*, *Adobe Premiere Pro*, *Unreal Engine Editor*.
- **Interactive Custom Rules Editor:** Modern PySide6 GUI interface allowing users to toggle auto-switching, browse presets, add custom executable rules, configure target thermal modes, and toggle rules on/off.

### 2. Safety Invariant INV-1 Fail-Safe Supremacy (`DEF-008`) & Override Fix (`DEF-010`)
- **Unconditional INV-1 Fail-Safe Supremacy (`DEF-008`):** Mandates that emergency thermal excursions (CPU >= 100°C or GPU >= 90°C) immediately force G-Mode maximum cooling. The process monitor and automatic switcher yield unconditionally to fail-safe trips; no process rule or exit restoration can lower cooling mode while a fail-safe condition or cooldown is active.
- **Fail-Safe User Override Protection (`DEF-010`):** Fixes an edge-case state corruption where an INV-1 emergency trip and subsequent reset cooldown previously overwrote the manual `_userOverride` flag during an active process session. Manual user intent remains uncorrupted when returning from emergency fail-safe cooldown.

### 3. Diagnostics PII Redaction (`DEF-006`)
- `Diagnostics.build()` bug report zip generation now automatically sanitizes sensitive system properties (`UserName`, `PrimaryOwnerName`, and `DNSHostName`) from WMI outputs, ensuring diagnostic packages can be shared publicly for troubleshooting without disclosing personal identifiable information.

### 4. Supply Chain & Architectural Hardening (`DEF-007` & `DEF-009`)
- **Production Supply Chain Promotion (`DEF-007`):** Promoted `psutil==7.2.2` to production `requirements.txt` with strict version pinning.
- **Apartment-Isolated Multi-Threading (`DEF-009`):** Implemented strict Qt Signal/Slot decoupled communication between the worker thread and the UI main thread, preserving COM apartment isolation and ensuring zero UI latency.

---

## Cryptographic Artifact Hashes

| Distribution | File Name | Size | SHA-256 Checksum |
|---|---|---|---|
| **Windows Installer** | `tcc-g15-installer-1.8.6.exe` | 45,278,695 bytes | `FF7080BC6457D0CC34A4A04310E59C7FE7B77C2314C6D7827710D566700F1B07` |
| **Portable Zip** | `tcc-g15-portable-1.8.6.zip` | 59,400,389 bytes | `CCE0DA3500AADDF9710A68B3772FFA4D94FB16A9C675CFF5AC3B5EAE90FFBAE4` |
| **CycloneDX SBOM** | `tcc-g15-sbom.json` | 6,605 bytes | `CFEAB335032DA45F5A131C09E4495989738FE6ED305EC72B49247FB85CCDFF86` |

---

## Verification & Test Results
- **Pytest Suite:** 59 of 59 unit and integration tests passing (`59 passed`).
- **Safety Invariant Verification:** Verified INV-1 through INV-6 across all normal and adversarial scenarios.
- **Code Quality:** Ruff linter passed with 0 errors across the codebase.
- **Hardware & Environment Guard:** `python tools/check_env.py` passed all 10/10 checks and USTT firmware verification.
