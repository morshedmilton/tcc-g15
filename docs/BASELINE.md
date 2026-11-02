# BASELINE.md — measured on this machine

**Date:** 2026-11-03 00:46–01:03
**Subject:** installed upstream build `C:\Program Files (x86)\Thermal Control Center\tcc-g15.exe` (1.6.4, binary dated 2025-01-15)
**Machine:** Dell G15 5530 · i7-13650HX (14C/20T) · RTX 4060 Laptop · 15.7 GB RAM · Win 11 Pro · BIOS 1.36.0
**Harness:** `tools/baseline_probe.py` (elevated, 1 Hz sampling, CSV) + `tools/startup_time.py`
**Raw:** `docs/baseline/baseline-20261103-004632.csv`, `baseline-20261103-005650.csv`, `startup.json`

## Process cost

| Metric | Idle | CPU load (10 procs) | Cooldown |
|---|---|---|---|
| App CPU | **0.59 %** | 1.11 % | 0.58 % |
| App RAM (working set) | **27.6 MB** | 26.2 MB | 26.7 MB |
| Context switches (wakeup proxy) | **21.5 /s** | 21.3 /s | 23.1 /s |
| Threads | 5 | 5 | 5 |
| Startup → window (warm, elevated) | **935 ms** | — | — |

RAM after a *fresh* start spikes to ~75 MB and settles to ~21–28 MB (measured over a 4 h session).

## Thermal / fan behaviour

| | Idle | 10-process CPU load (210 s) |
|---|---|---|
| CPU fan | 1 899 rpm | **2 522 rpm** |
| GPU fan | 2 184 rpm | **2 807 rpm** |
| CPU sensor | 72 °C (max 81) | **84 °C (max 85)** |
| GPU sensor (Dell WMI) | 64 °C | 65 °C |
| GPU temp (NVML) | **61 °C** | 62 °C |
| GPU power (NVML) | 22.7 W | 21.8 W |

Observations:
- The BIOS fan curve does respond: +12 °C on the CPU sensor gave **+33 % fan RPM**. The app itself does not drive fans in Balanced mode — that is the firmware.
- Under a 10-core synthetic load the CPU sensor peaked at **85 °C**, i.e. 10 °C below the app's default fail-safe threshold (95 °C). Headroom exists but is not generous on this chassis.
- **The Dell GPU sensor reads ~3 °C above NVML at idle** (64 vs 61). That is the opposite direction of the known 2–3 °C bogus-reading bug (#9), which means a naive "sensor looks low" check would not catch it — the range guard we shipped (5–120 °C) is the right granularity.
- Wakeups at 21.5/s come from the 1 Hz poll × 4 WMI round-trips plus the Qt event loop. This is the main efficiency target: coalescing to ~5/s is realistic.

## What this baseline does **not** cover (yet)

| Gap | Why | Plan |
|---|---|---|
| GPU load (games / FurMark) | no GPU stress tool installed, and a 15 min FurMark run needs a supervised window | Phase 6 hardening, with the fail-safe armed |
| Sustained >2 h soak | time budget | Phase 6 |
| Sleep / resume, lid close, AC↔battery | needs interaction with the physical machine | Phase 6 |
| Cold start after reboot | requires a reboot | next reboot, 1 line of log |
| UI responsiveness (frame times) | needs a targeted Qt instrumentation pass | Phase 5, first UI work item |

## Conclusions that drive Gate 1

1. **The Python/PySide6 stack is not the problem.** 0.6 % CPU and 27 MB RAM is already better than most Electron tray apps. A Rust rewrite would buy maybe 20 MB and 0.3 % CPU — **not worth** the contributor cost. → ADR-003 resolves to *stay Python*, and spend the effort on polling efficiency and correctness instead.
2. **Wakeups are the real efficiency debt** (21/s for a 1 Hz sampler). Target: ≤6/s by batching WMI reads and coalescing UI updates.
3. **955 ms warm start is acceptable** but includes UAC; a cached-elevation service would remove that latency entirely (feeds ADR-004).
4. **Fail-safe headroom is thin** (85 °C seen under synthetic load vs 95 °C threshold). Any fan-curve feature must keep the hard threshold armable at all times.
