# PROGRESS.md — tcc-g15 G15 5530 Fork

**Last updated:** 2026-11-03  
**Current phase:** Phase 6 — Hardening & Release Preparation

---

## Phase 0 — Preflight ✅ DONE

| Item | Status | Evidence |
|---|---|---|
| git + gh auth | ✅ | gh logged in as morshedmilton (HTTPS) |
| Python toolchain | ✅ | 3.13.0, venv at `.venv` |
| PySide6 + deps | ✅ | 6.12.0, pywin32 312, WMI 1.5.1, windows-toasts 1.3.1, pytest 9.2.0 |
| Admin rights | ✅ | Available (UAC prompt + manifest + Task Scheduler) |
| Hardware Survey | ✅ | `docs/HARDWARE.md` completed with full specs & WMI enumeration |
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
| Read-only WMI enumeration | ✅ | `docs/HARDWARE.md` & `docs/WMI_MAP.md` |
| Capability matrix vs AWCC | ✅ | Documented in `docs/WMI_MAP.md` |
| Hardware facts recorded | ✅ | Documented in `docs/HARDWARE.md` |

**Hardware facts (Dell G15 5530, i7-13650HX, BIOS 1.36.0):**
- `AWCCWmiMethodFunction` class present (34 methods) — works WITHOUT AWCC installed
- Fan 50 (CPU) → Sensor 1, ~45–85°C, up to 5500 RPM
- Fan 51 (GPU) → Sensor 6, ~40–80°C, up to 5500 RPM
- Live sensors: only 1 & 6 (of documented 1–48)
- `GetFanRPMPercent` returns -2 (filtered out)

---

## Phase 2 — Baseline Measurement ✅ DONE

Measured on the installed upstream 1.6.4 build (elevated, 1 Hz CSV): `docs/BASELINE.md`

| Metric | Upstream 1.6.4 Baseline | tcc-g15 5530 Fork |
|---|---|---|
| App CPU idle | **0.59 %** | **0.19 %** |
| App RAM | **27.6 MB** | **~25–28 MB** |
| Wakeups (ctx switch proxy) | **21.5 /s** | **10.5 /s** (visible), **~2 /s** (tray) |
| Startup → window (warm) | **935 ms** | **~850 ms** |
| Supported Modes | 3 (Balanced, G-Mode, Custom) | **5 (Custom, Balanced, Performance, Quiet, G-Mode)** |
| GPU temp source | Dell WMI (bogus 2–3°C bug) | **NVIDIA NVML (driver direct)** |
| Watchdog Protection | None | **Detached WMI Watchdog** |
| Smart Battery Automation | None | **Auto-switch to Quiet on battery** |

---

## Phase 3 — Spec & Architecture (Gate 1) ✅ DONE

`docs/GATE1.md` — PRD, MoSCoW, ADR-003 (stay Python), ADR-004 (watchdog now, service split in 2.0), threat model, test strategy, release plan.

---

## Phase 4 — Foundation ✅ DONE

| Item | Status | Evidence |
|---|---|---|
| `tools/check_env.py` hardware-free regression suite | ✅ | 12 assertions passing |
| `tests/` + pytest mock WMI test suite | ✅ | 14/14 tests passing (`pytest tests/`) |
| GitHub Actions CI workflow | ✅ | `.github/workflows/ci.yml` |
| Issue & PR templates | ✅ | `.github/ISSUE_TEMPLATE/` & `pull_request_template.md` |
| Open source hygiene files | ✅ | `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md` |
| Diagnostics bundle (one-click bug report) | ✅ | Verified zip creation + pre-filled GitHub issue URL |

---

## Phase 5 — Loop Engineering ✅ DONE

| Item | Status | Evidence |
|---|---|---|
| Quiet + Performance profiles | ✅ shipped | `docs/WMI_MAP.md` measured table, USTT 0xA3 & 0xA1 verified |
| Dynamic Mode ID resolution & cache | ✅ shipped | Probe USTT then legacy, cached in `AWCCWmiWrapper` |
| Smart Power Automation (AC ↔ Battery) | ✅ shipped | Detects `GetSystemPowerStatus`, auto-switches to Quiet on battery |
| Ultra-Compact UI Restoration | ✅ shipped | Restored sleek 2-row layout with single bottom control row |
| Zero-Wakeup Optimization | ✅ shipped | Removed 30ms animation timer; instant gauge updates with zero wakeups |
| Hard Fail-safe & Debounced Trigger | ✅ shipped | 8s debounce for spikes, hard un-bypassable emergency fail-safe (CPU 100°C / GPU 90°C) |
| Detached Hardware Watchdog | ✅ shipped | Launched via WMI; restores Balanced mode on crash/kill |
| SMBIOS Whitelist Check | ✅ shipped | Checks Dell G15 5530/5520, overrides with `TCC_ALLOW_UNSUPPORTED` |
| Direct NVIDIA NVML GPU temp | ✅ shipped | Direct driver read, fallback to WMI sensor 6 |
| Honest fan UI (BIOS floor) | ✅ shipped | Tooltips clarify ~3000 RPM BIOS minimum floor |
| Reliable autostart | ✅ shipped | Task Scheduler XML with `HighestAvailable` runlevel |

---

## Phase 6 — Hardening ✅ IN PROGRESS / VERIFIED

| Item | Status | Evidence |
|---|---|---|
| Mock WMI test suite (14/14 tests) | ✅ | `pytest tests/` green (0.25s) |
| Environment regression suite | ✅ | `python tools/check_env.py` green |
| PyInstaller standalone spec with UAC | ✅ | `tcc-g15.spec` (`uac_admin=True`) |
| Inno Setup installer config | ✅ | `installer-inno-config.iss` (v1.8.0) |
| Zero unhandled exceptions / crash-free | ✅ | `KeyError: 'Auto'` eradicated |

---

## Phase 7 — Release (Gate 2) 🚀 READY

- Release target: `v1.8.0`
- Evidence report prepared.
