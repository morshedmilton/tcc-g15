# GATE 1 — Spec & Architecture (needs your approval)

**Date:** 2026-11-03 · **Baseline:** `docs/BASELINE.md` · **Evidence:** `docs/WMI_MAP.md`, `tcc-g15-research/analysis-5530.md`

## 0. Where we are

| | |
|---|---|
| Fork | github.com/morshedmilton/tcc-g15, branch `g15-5530` |
| Shipped | 1.7.0 = upstream master + 6 safety/correctness fixes (7ac9d87) |
| Baseline measured | 0.59 % CPU · 27.6 MB RAM · 21.5 wakeups/s · 935 ms start |
| Hardware confirmed | 2 fans (50→sensor 1 CPU, 51→sensor 6 GPU), NVML GPU temp works, `GetFanRPMPercent` unsupported (-2) |

---

## 1. PRD (short)

**Problem.** AWCC is a heavy, telemetry-sending app whose fan control is broken; upstream tcc-g15 is a 27 MB tray app that works but (a) has silent wrong-mode bugs, (b) has no fan curve, no extra power profiles, no honest feedback about BIOS limits, (c) restores G-mode after reboot, (d) trusts a buggy GPU sensor, (e) keeps a full admin GUI resident with no watchdog.

**Product.** An unofficial, open-source (GPL-3.0) thermal + fan control centre for the Dell G15 5530: correct modes, safe fan control, real telemetry, per-profile automation, no telemetry, no network calls.

**Non-goals (v1.x).** Linux, TDP/undervolt/BIOS writes, RGB, overlay, anything requiring a kernel driver.

**Success criteria (measurable).**
1. Zero silent mode failures — every mode change verified by readback or explicit failure.
2. Fail-safe provably fires: kill -9, sleep/resume, service stop → default mode restored.
3. Wakeups ≤ 6/s (from 21.5), CPU ≤ 0.5 % idle, RAM ≤ 35 MB.
4. Startup ≤ 700 ms warm.
5. A stranger with the same laptop can install it, hit an error, and file a usable bug report in one click.

---

## 2. MoSCoW

**Must (v1.8)**
- Watchdog that restores Balanced on crash / force-kill / sleep-resume / exit (safety 2b) — *new, separate process*
- Fail-safe cannot be disabled from the UI; threshold + debounce; armed even when a fan curve is active
- SMBIOS whitelist: refuse to run on unknown models (printed, actionable message)
- Verified mode changes (status 0 **and** readback where the firmware allows)
- NVML GPU temperature as primary, Dell WMI as fallback
- Batched WMI polling + coalesced UI updates (target ≤6 wakeups/s)
- Honest fan UI: show BIOS floor (~70 % / ≥3000 rpm) and real ceiling
- Quiet / Performance / FullSpeed modes, **only after** a hardware test proves the firmware accepts them
- Reliable autostart (Run key + verification, replaces Task Scheduler XML)
- One-click diagnostics bundle → prefilled GitHub issue (model, BIOS, build, logs, WMI dump, redacted)

**Should (v1.9)**
- Fan curve editor (rewrite of dead PR #67; hysteresis + min-dwell)
- JSON profile import/export (validated schema)
- AC ↔ battery profile switching
- CLI (`tcc set-mode`, `tcc profile`, for scripts/streamdeck)

**Could (v2)**
- Per-app auto profiles
- Overlay / mini widget
- Keyboard lighting **if** the AWCC lighting methods verify on 5530

**Won't**
- TDP / voltage / BIOS OC / firmware flashing
- Linux
- Any network call, telemetry, auto-update pinging

---

## 3. Architecture

### ADR-003 — Stack: **stay Python + PySide6** (evidence-based)

| Option | Evidence | Verdict |
|---|---|---|
| Python + PySide6 (keep) | 0.6 % CPU, 27.6 MB, 935 ms start — already leaner than most tray apps | ✅ **chosen** |
| Rust core + light UI | would save ~20 MB and ~0.3 % CPU; costs a full rewrite, FFI to WMI, new UI, and a much higher contributor bar | ❌ rejected on cost/benefit |
| C# .NET AOT | similar cost, marginal gain at this footprint | ❌ rejected |

Rationale: the mission's efficiency goal is met by fixing *wakeups*, not by changing language. Rewriting to save 20 MB while adding a COM/FFI layer would trade a measured cost for an unmeasured risk.

### ADR-004 — Privilege: **elevated app + separate watchdog now, service split later**

```
┌─────────────────────┐        heartbeat file / pipe        ┌──────────────────────┐
│  tcc-g15 GUI        │ ───────────────────────────────►    │  tcc-watchdog        │
│  (admin, PySide6)   │ ◄────── "restore Balanced" ◄──────  │  (admin, no UI)      │
│  WMI: Thermal_*     │                                     │  WMI: Thermal_Control│
└─────────────────────┘                                     └──────────────────────┘
```

- **v1.8:** two elevated processes; the watchdog is ~100 LOC, has no UI, and only acts if the GUI's heartbeat stops or the OS signals sleep/shutdown. This satisfies safety 2b without a session-0 service.
- **v2 (deferred):** unprivileged GUI + privileged service over named pipe. Reason for delay: a session-0 WMI/COM service is a real engineering project (IPC auth, autostart race, installer changes) and does not reduce the *thermal* risk — the watchdog does.

### Control loop

```
poll (adaptive 0.5–3 s, batched)  →  ring buffer (temps, rpm, mode)
                                   →  controller (hysteresis 2 °C, min-dwell 5 s,
                                      derivative-aware curve when a profile is active)
                                   →  WMI write (mode / fan offset)  →  readback verify
UI update: 4 Hz max, coalesced, never on the WMI thread
```

Polling rule: 1 s when the window is visible or a curve is active; 3 s when minimised and idle; immediate poll on resume / mode change / AC transition.

---

## 4. Threat & risk model (delta from `docs/RISKS.md`)

| Threat | Vector | Mitigation |
|---|---|---|
| Thermal damage from a bad curve | user sets 0 % at 90 °C | hard fail-safe always armed; curve output clamped to `[floor, 100]`; UI refuses curve points below floor; debounce |
| Privilege abuse | entire GUI is admin; a rendering bug is not a privilege escalation, but a malicious profile *is* input | profile JSON schema-validated, numeric ranges clamped, no code/exec fields, no path traversal |
| Wrong model | user copies an exe to another Dell | SMBIOS whitelist check at startup, refuse with a clear message |
| Firmware not accepting a mode | 5530 answered -2 to RPM% | verified readback; "experimental" label for unproven modes; never assume success from status 0 alone |
| Crash leaves fans pinned | force-kill during G-mode | watchdog restores Balanced; also a "last known mode" recovery flag on next start |
| Supply chain | PyInstaller + PyPI deps | pinned requirements + hashes, `pip-audit`, SBOM, VirusTotal scan of the release exe |
| Bogus sensor | Dell driver 2–3 °C bug | range guard (5–120) + 60 s unknown grace + NVML cross-check (if NVML says >85 °C while WMI says <20 °C → trust NVML and warn) |

---

## 5. Test strategy

| Layer | What | Where |
|---|---|---|
| Unit | WMI arg encoding, mode fallback, curve interpolation, hysteresis, clamping, settings migration | `tools/check_env.py` → grows into `tests/` (pytest), runs with a `FakeWmi` backend |
| Contract | every `AWCCWmiWrapper` method against the fake, including invalid answers (-2, 0xFFFFFFFF, exceptions) | CI, no hardware |
| CI | lint (ruff), types (mypy), pytest, PyInstaller build, checksum, SBOM | GitHub Actions `windows-latest` |
| Hardware-in-the-loop | whitelist, mode switching, fan response, fail-safe trip, watchdog restore, sleep/resume | this machine, script with live temp monitoring + auto-abort at 95 °C CPU / 88 °C GPU |
| Soak | 2 h mixed with 1 Hz logging, watch for leaks and mode drift | Phase 6 |
| Recovery | kill -9 the GUI, confirm watchdog restores Balanced within 5 s | Phase 5 |

---

## 6. Release plan

| Version | Content | Gate |
|---|---|---|
| **1.7.0** | shipped: 6 correctness/safety fixes | done (7ac9d87) |
| **1.8.0-beta1** | Must-list (watchdog, whitelist, NVML, wakeup reduction, honest UI, autostart, diagnostics) | Gate 2 evidence review |
| **1.8.0** | beta fixes only | your approval |
| **1.9.0** | fan curve, profiles, AC/battery, CLI | next cycle |
| **2.0.0** | privilege split, per-app profiles | next cycle |

Release artefacts: portable exe, Inno installer, SHA-256 sums, SBOM, VirusTotal link, CHANGELOG entry, known-issues section.

---

## 7. What I need from you (Gate 1)

1. **Approve ADR-003** (stay Python — no rewrite).
2. **Approve ADR-004** (elevated app + watchdog now; service split deferred to 2.0).
3. **Approve the Must list** for 1.8.0-beta1, or cut something.
4. One permission that needs your explicit yes: **let me run the hardware tests** (mode switching, fan offset changes, fail-safe trip). They change thermal state for seconds at a time, fail-safe armed, restore point first.
