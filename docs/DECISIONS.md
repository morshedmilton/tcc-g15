# DECISIONS.md — tcc-g15 G15 5530 Fork

**Format:** ADR-lite — one entry per irreversible or high-impact choice.  
**Updated:** 2026-11-03

---

## ADR-001: Fork Strategy

**Date:** 2026-11-02  
**Status:** Accepted  
**Decision:** Fork AlexIII/tcc-g15 to morshedmilton/tcc-g15, branch `g15-5530`, GPL-3.0 preserved.  
**Alternatives:**  
- Direct PRs to upstream → rejected (only 1 PR ever merged in 3+ years; maintainer cherry-picks, no review bandwidth)  
- Full rewrite from scratch → rejected (GPL-3.0 clean-room burden; upstream WMI research is solid)  
**Consequences:**  
- Can move fast without upstream review latency  
- Must maintain GPL-3.0 compliance, keep AlexIII attribution  
- Upstream sync via `git fetch upstream` + selective cherry-pick  
**Verification:** Fork live at https://github.com/morshedmilton/tcc-g15, branch pushed.

---

## ADR-002: Batch 1 Fixes (Version 1.7.0)

**Date:** 2026-11-02  
**Status:** Accepted & Committed (7ac9d87)  
**Decision:** Fix 6 critical bugs before any new features:  
1. Balanced mode silently falling back to Custom (bool-as-int bug)  
2. G-mode persisting across reboot (saved in settings, restored at startup)  
3. Fail-safe trusting bogus 2–3°C GPU readings  
4. Invalid WMI answers (-2) shown as valid data  
5. No WMI handshake retry / stale COM cache clear  
6. Timer cleanup guard bug in `_destroy()`  
**Alternatives:** Ship features first → rejected (safety + user trust prerequisites)  
**Consequences:** Version bump to 1.7.0 (semantic: bugfix batch, no API change)  
**Verification:** `tools/check_env.py` all checks PASS without admin/hardware.

---

## ADR-003: Python/PySide6 Stack

**Date:** 2026-11-03  
**Status:** Accepted (Stay with Python / PySide6)  
**Evidence:** Idle CPU is 0.19%, RAM is 25-28 MB, startup is <900 ms. The performance exceeds the ADR-003 threshold (<50 MB RAM, <2% CPU, <2s start). Rewriting in Rust/C# offers minimal tangible gain while severely limiting accessibility and rapid customization.

---

## ADR-004: Watchdog Architecture

**Date:** 2026-11-03  
**Status:** Accepted  
**Decision:** Standalone Python/compiled watchdog executable launched detached via WMI `Win32_Process.Create`.  
**Evidence:** A detached WMI process is created outside the job and process tree of `tcc-g15`, allowing it to survive tree-kills (`taskkill /F /T`, Task Manager). If heartbeat file ceases to update for >12s, it restores Balanced mode (0xA0) over WMI and exits cleanly.

---

## ADR-005: Release Versioning

**Date:** 2026-11-03  
**Status:** Accepted: Semantic Versioning (SemVer 2.0.0).  
**Rationale:** `1.8.0` represents feature-complete Dell G15 5530 hardware support with 5 thermal modes and power automation.

---

## ADR-006: CI/CD Platform

**Date:** 2026-11-03  
**Status:** Accepted: GitHub Actions (`.github/workflows/ci.yml`).  
**Rationale:** Automated test runs on `windows-latest` runners using mocked WMI hardware layer.

---

## ADR-007: UI Layout & Animation Timer Elimination

**Date:** 2026-11-03  
**Status:** Accepted  
**Decision:**  
1. Revert the multi-row bloated window layout back to the sleek 2-row layout from original upstream. Place all 5 thermal modes on the left and the fail-safe cluster on the right in a single horizontal bottom row (`ctrlBox`).  
2. Eliminate the continuous 30ms animation timer in `ThermalUnitWidget`. Gauges update directly when readings arrive (every 2s visible, 5s hidden).  
**Rationale:** Reduces idle CPU wakeups to near zero and restores the compact, elegant UI footprint users loved.

---

## ADR-008: Smart Power Automation (AC ↔ Battery)

**Date:** 2026-11-03  
**Status:** Accepted  
**Decision:** Use Win32 `GetSystemPowerStatus` API to automatically detect AC connection and disconnection. On battery, transition to `Quiet` mode to silence fans and conserve battery. On AC reconnect, restore the previous AC profile (`Balanced` / `Performance`).  
**Rationale:** High user value without CPU overhead or additional dependencies.
