Beta for the Dell G15 5530 fork. **Unofficial**, GPL-3.0, no telemetry, no network calls.

## What changed since upstream 1.6.4

**Safety**
- Watchdog process: if the app crashes or is force-killed, it restores Balanced within ~13 s (verified on a G15 5530 with `taskkill /T`). It is launched through WMI, so it is not killed with the app.
- Fail-safe keeps a plausibility guard (5–120 °C) and a 60 s grace before a silent sensor may trip it — a bogus 2–3 °C reading can no longer switch the machine into G-mode.
- Unknown laptop models are refused unless `TCC_ALLOW_UNSUPPORTED=1` is set.

**Features**
- Quiet and Performance profiles. The firmware id is resolved on first use: this board answers only the USTT ids (`0xA3` Quiet, `0xA1` Performance) and rejects the plain `150`/`152` that other Dell boards accept.
- "Create bug report" in the tray menu: redacted diagnostics zip (model, BIOS, firmware dump, log) plus a prefilled issue.
- GPU temperature now comes from NVML instead of Dell's WMI sensor.

**Efficiency** (measured on a G15 5530, i7-13650HX, BIOS 1.36.0)
- wakeups 21.5 → 10.5 per second (2 s poll, 5 s while hidden)
- app CPU 0.59 % → 0.19 % idle

**Fixes**
- "Balanced" no longer silently selects Custom when the firmware rejects the USTT probe.
- G-mode is no longer restored at startup (after a reboot the fans came up at full blast).
- Invalid WMI answers (this board answers `-2`) are rejected instead of displayed.
- Autorun verifies the scheduled task exists instead of trusting the exit code.
- Timer cleanup on exit used the wrong object.

## Install

Run `tcc-g15-installer-1.8.0-beta1.exe` as administrator. It upgrades an existing Thermal Control Center install (same AppId).

SHA-256: see `SHA256SUMS.txt`.

## Known issues

- Switching to or from G-mode can still cause a short system-wide freeze — that is Dell's thermal interface, not this app.
- Manual fan control is an offset over the BIOS curve; the BIOS keeps a floor around 70 % / 3000 rpm.
- Keyboard lighting and power limits are not implemented (the WMI methods exist but are unverified on this board).
- Beta: sleep/resume and a 2 h soak are not yet verified on hardware.
