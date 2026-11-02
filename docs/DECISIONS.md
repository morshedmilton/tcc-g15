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

## ADR-003: Python/PySide6 Stack — PENDING MEASUREMENT

**Date:** 2026-11-03  
**Status:** Deferred to Phase 2 data  
**Options:**  
| Option | Pros | Cons | Decision Trigger |
|---|---|---|---|
| Stay Python + PySide6 | Contributor-friendly, fast iteration, existing codebase | Higher RAM/CPU, slower startup, GIL limits polling precision | If baseline shows <50 MB RAM, <2% CPU idle, <2 s cold start → keep |
| Rewrite core in Rust (AOT) + light UI (Tauri/egui/Slint) | Tiny binary, zero GC pauses, fearless concurrency, better startup | Steeper contributor bar, FFI to WMI, UI rewrite effort | If baseline >100 MB RAM or >3% CPU idle or >3 s cold start → rewrite core |
| C# (.NET 8 AOT) + WinUI 3 | Native Windows, great tooling, AOT, single binary | Larger binary than Rust, WinUI 3 maturity, less cross-platform | If team has C# expertise and baseline mediocre → consider |
**Decision Rule:** Evidence from Phase 2 baseline (RAM, CPU, wakeups, startup time) decides. No assumption.

---

## ADR-004: Privilege Split Architecture — PENDING GATE 1

**Date:** 2026-11-03  
**Status:** Deferred to Gate 1  
**Options:**  
- **A:** Current — whole GUI runs as admin (simple, but over-privileged)  
- **B:** Minimal elevated service (Windows Service or scheduled task with highest) owning WMI handle + watchdog; unprivileged GUI talks via named pipe / localhost HTTP  
- **C:** Auto-elevate only for WMI calls via COM elevation moniker (complex, fragile)  
**Decision Criteria:** Phase 2 baseline attack surface + UX friction measurement. Safety principle 2b (watchdog) favors B.

---

## ADR-005: Release Versioning — PENDING

**Date:** 2026-11-03  
**Status:** Deferred  
**Options:** SemVer (1.7.0, 1.8.0, 2.0.0) vs CalVer (2026.11, 2026.12)  
**Lean:** SemVer — communicates breaking changes clearly for a driver-adjacent tool.

---

## ADR-006: CI/CD Platform — PENDING

**Date:** 2026-11-03  
**Status:** Deferred to Phase 4  
**Likely:** GitHub Actions (windows-latest runners, mock WMI layer for unit tests).

---

## Skill Commit Tracking

| Skill | Commit / Version | Date Read | Purpose |
|---|---|---|---|
| 9router (index) | master @ raw.githubusercontent.com/decolua/9router/refs/heads/master/skills/9router/SKILL.md | 2026-11-02 | AI gateway for independent review, web research |
| 9router-chat | (fetch on demand) | — | Code review by different model |
| 9router-web-search | (fetch on demand) | — | Current WMI/Windows/Dell findings |
| 9router-web-fetch | (fetch on demand) | — | Fetch specific technical pages |