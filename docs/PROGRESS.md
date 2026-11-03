# PROGRESS.md — tcc-g15 G15 5530 Fork

**Last updated:** 2026-11-03  
**Current phase:** Phase 2 — Baseline measurement

---

## Phase 0 — Preflight ✅ DONE

| Item | Status | Evidence |
|---|---|---|
| git + gh auth | ✅ | gh logged in as morshedmilton (HTTPS) |
| Python toolchain | ✅ | 3.13.15, venv at `.venv` |
| PySide6 + deps | ✅ | 6.12.0, pywin32 312, WMI 1.5.1, windows-toasts 1.3.1 |
| Admin rights | ✅ | Available (UAC prompt works) |
| 9router env | ✅ | http://localhost:20128/v1, key stored, model `gg` |
| Disk space | ✅ | C: 149 GB free |
| Fork created | ✅ | https://github.com/morshedmilton/tcc-g15 |
| Branch pushed | ✅ | `g15-5530` at origin |

---

## Phase 1 — Discovery & Audit ✅ DONE

| Item | Status | Evidence |
|---|---|---|
| Full codebase read | ✅ | 10 source files (Backend 3, GUI 7) + WMI doc |
| Upstream issues/PRs surveyed | ✅ | 93 issues, 8 PRs (only 1 merged); `tcc-g15-research/upstream-evidence.md` |
| Notable forks checked | ✅ | the0cp/tcc-g15 (no meaningful divergence), Lumine (hotkey config only) |
| Last upstream activity | ✅ | master 8 commits ahead of 1.6.4; latest commit 2026-05-09; 1.6.4 release 2025-01-18 |
| Read-only WMI enumeration | ✅ | `tools/hwprobe.py` → `tcc-g15-research/hwprobe-5530.json` |
| Capability matrix vs AWCC | ✅ | Documented in `analysis-5530.md` |
| Hardware facts recorded | ✅ | See below |

**Hardware facts (Dell G15 5530, i7-13650HX, BIOS 1.36.0):**
- `AWCCWmiMethodFunction` class present (34 methods) — works WITHOUT AWCC installed
- Fan 50 (CPU) → Sensor 1, ~66°C, 3826 RPM
- Fan 51 (GPU) → Sensor 6, ~53°C, 4013 RPM
- Live sensors: only 1 & 6 (of documented 1–48)
- `GetFanRPMPercent` returns -2 (now filtered)

---

## Phase 2 — Baseline Measurement ✅ DONE

Measured on the installed upstream 1.6.4 build (elevated, 1 Hz CSV): `docs/BASELINE.md`

| Metric | Value |
|---|---|
| App CPU idle | **0.59 %** |
| App RAM | **27.6 MB** (75 MB right after start) |
| Wakeups (ctx switch proxy) | **21.5 /s** |
| Startup → window (warm) | **935 ms** |
| CPU fan at 72 °C / at 84 °C | 1 899 → 2 522 rpm |
| GPU fan at 64 °C / at 65 °C | 2 184 → 2 807 rpm |
| CPU sensor peak under 10-proc load | **85 °C** |
| GPU temp: Dell WMI vs NVML | 64 °C vs **61 °C** (Dell reads +3) |

Gaps: no GPU-load run, no 2 h soak, no sleep/resume (all Phase 6).

---

## Phase 3 — Spec & Architecture (Gate 1) ✅ PACKAGE READY — awaiting approval

`docs/GATE1.md` — PRD, MoSCoW, ADR-003 (stay Python), ADR-004 (watchdog now, service split in 2.0), threat model, test strategy, release plan.

| Task | Status |
|---|---|
| PRD + MoSCoW | ✅ |
| Architecture decision (privilege split, stack choice) | ✅ evidence-based, needs approval |
| Threat/risk model | ✅ |
| Test strategy | ✅ |
| Release plan | ✅ |
| **Gate 1 presentation** | ✅ sent, waiting |

---

## Phase 4 — Foundation 🔄 PARTIAL

| Item | Status |
|---|---|
| `tools/check_env.py` as the hardware-free regression suite (12 assertions) | ✅ |
| `tests/` + pytest + ruff + mypy + CI workflow | ⬜ |
| CONTRIBUTING / SECURITY / CODE_OF_CONDUCT / issue templates | ⬜ |
| Diagnostics bundle (one-click bug report) | ⬜ |

## Phase 5 — Loop Engineering 🔄 IN PROGRESS

| Item | Status | Evidence |
|---|---|---|
| Quiet + Performance profiles | ✅ shipped | `docs/WMI_MAP.md` measured table, commit c918f23 |
| Mode id resolution per firmware (no more fixed ids) | ✅ | `check_env.py` covers USTT + legacy + unsupported + Custom(0) |
| Watchdog (restore Balanced on crash/kill) | ✅ verified | hard-kill test: fired at 13 s, restored Balanced, exited (`docs/baseline/watchdog.result.txt`). Launched via WMI so it survives `taskkill /T` |
| SMBIOS whitelist | ✅ | refuses unknown models unless `TCC_ALLOW_UNSUPPORTED=1` |
| NVML GPU temperature | ✅ | primary source, Dell WMI as fallback; prints which one it uses |
| Wakeup reduction | ✅ 21.5 → **10.5 /s** (2 s poll, 5 s hidden); CPU 0.59 → **0.19 %** | measured `probe3/probe4` |
| Honest fan UI (BIOS floor) | ✅ tooltip explains the floor, no fake promise | — |
| Reliable autostart | ✅ verifies the task with `schtasks /query`, writes the XML to temp | — |
| Diagnostics bundle | ✅ verified: zip (system/wmi/awcc/README) + prefilled issue URL, no serials | `docs/baseline/diag2.log` |

---

## Phase 6 — Hardening ⬜ PENDING

---

## Phase 7 — Release (Gate 2) ⬜ PENDING

---

## Phase 8 — Post-release ⬜ PENDING

---

## Open Questions / Decisions Needed

| # | Question | Where Tracked |
|---|---|---|
| 1 | Keep Python/PySide6 or rewrite core in Rust/C#? | DECISIONS.md (after Phase 2 data) |
| 2 | Privilege split: elevated service + IPC? | DECISIONS.md |
| 3 | Exact fan curve editor scope (PR #67 rewrite)? | DECISIONS.md |
| 4 | Keyboard lighting support on 5530? | WMI_MAP.md (need enumeration) |
| 5 | SemVer vs CalVer for releases? | DECISIONS.md |

---

## Next Actions (Immediate)

1. Package 1.8.0-beta1: PyInstaller exes (app + watchdog) + Inno installer
2. Soak + sleep/resume checks (Phase 6)
3. Gate 2 evidence pack for the beta tag