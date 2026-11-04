# CYCLE 007 — Auto profile restored, four-profile selector, audit fixes

**Date:** 2026-11-04
**Version:** 1.8.7
**Branch:** `cycle-007/auto-profile`
**Trigger:** owner directive (2026-11-04) — the window must offer exactly `Auto`, `Balanced`, `G-Mode`, `Custom`, with an automatic temperature→fan curve (50 °C ≈ 3500 rpm, 80 °C+ = full speed), and the UI must stop clipping.

## Why this cycle exists

`v1.8.6` shipped five firmware profiles (`Custom`, `Balanced`, `Performance`, `Quiet`, `G_Mode`) and dropped the owner's `Auto` curve entirely. The owner's stated product requirement was unmet — a P1 requirement gap, not a missing feature request.

## What changed

| ID | Change | Evidence |
|---|---|---|
| REQ-701 | `Auto` profile restored; window/tray show exactly `Auto`, `Balanced`, `G-Mode`, `Custom` | `MODE_ORDER` in `src/GUI/AppGUI.py`; screenshot `docs/baseline/cycle007-h196.png` |
| REQ-702 | `src/Backend/FanCurve.py`: piecewise-linear curve, 50 °C → 64 %, 80 °C → 100 %, clamped and monotonic; per-fan deadband 3 points + 1.5 s rate limit; `None` sensor never writes | `tests/test_fan_curve.py` (23 assertions) |
| REQ-703 | `Auto` selects firmware `Custom` (offsets are only honoured there) and drives both fans from their own sensor | `onModeChange` / `onTelemetryReady` |
| DEF-704 | `Auto` added to `COOLING_SEVERITY_ORDER` at the old Performance slot, so rules cannot outrank it with `Balanced` | `test_auto_outranks_balanced_in_arbitration` |
| DEF-702 | An automatic switch failure no longer takes the fatal user-command path (which stopped the watchdog without restoring `Balanced`) | `onModeChange` automatic branch |
| DEF-708 | `"enabled": "false"` no longer parses as `True` | `_as_bool`, `test_enabled_false_string_is_honoured` |
| DEF-711 | Rules dialog offers exactly the four visible profiles | `SUPPORTED_MODES`, `test_dialog_offers_exactly_the_window_profiles` |
| UI clip | Window sized from the control row instead of a 360-400 px clamp: 574 × 234 confirmed on hardware | `cycle007-wide.png`, `cycle007-h196.png` |

## Verification

```
pytest tests/ -q          -> 82 passed
ruff check .              -> All checks passed
tools/check_env.py        -> ALL CHECKS PASSED
```
Hardware: app launched elevated, four buttons rendered in the owner's order (`AUTO CUSTOM BALANCED G-MODE` visible; `BALANCED` selected), window 574 × 234, no clipped row. Fan RPM cross-checked with `tools/restore_default_mode.py --probe` (2120 / 2383 rpm at 78 / 63 °C).

## Open defects found during this cycle (not fixed here)

| ID | Sev | Summary |
|---|---|---|
| DEF-716 | P1 | TACH gauge shows `0 RPM` while the hardware reports ~2100 rpm — telemetry worker rpm read needs investigation (temperature and mode paths unaffected) |
| DEF-701 | P1 | Manual mode click during a latched fail-safe is not recorded as an override and clears the latch, so the rule fights the user (audit §3) |
| DEF-703/705/706/707/709/710/712-715 | P2/P3 | Recorded in `docs/engineering/audit/CYCLE-007/backend-process-switching.md` for Cycle 008 |

## Not claimed

- No claim that the Auto curve reaches an exact rpm: the EC owns the real fan curve; the curve is expressed in percent with measured equivalents.
- No claim that `Performance`/`Quiet` are gone from the firmware — they remain reachable through old configs, which are migrated to `Auto`/`Balanced` at load.
