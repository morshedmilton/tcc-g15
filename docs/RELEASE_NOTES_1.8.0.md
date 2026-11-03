# Release Notes — tcc-g15 v1.8.0 (Dell G15 5530 Edition)

**Official Release:** v1.8.0  
**License:** GPL-3.0  
**Target Platform:** Dell G15 5530 (and compatible G15 systems), Windows 10/11  
**Maintainer:** Md. Morshed Milton (@morshedmilton)  
**Original Author & Core WMI Research:** AlexIII (@AlexIII)

---

## Highlights

This release completes the transformation of `tcc-g15` into a modern, lightweight, highly efficient, and rock-solid alternative to Alienware Command Center (AWCC) tailored specifically for the **Dell G15 5530**:

1. **Restored Ultra-Compact Sleek UI:**
   - Full restoration of the original 2-row compact window layout.
   - All 5 modes and fail-safe controls live harmoniously on a single bottom control row without vertical stretching, blank spaces, or bloated window dimensions.

2. **Full 5 Verified Thermal Modes:**
   - **Balanced (0xA0):** Default everyday thermal balance.
   - **Performance (0xA1):** High sustained performance with aggressive cooling for gaming/rendering.
   - **Quiet (0xA3):** Acoustic-optimized low-noise profile for study or quiet environments.
   - **G-Mode (0xAB):** Game Shift 100% maximum fan cooling.
   - **Custom (0x00):** Manual user fan control sliders with honest tooltips highlighting the ~3000 RPM BIOS minimum floor.

3. **Smart Power & Battery Automation:**
   - Detects AC vs Battery power state instantly via Win32 API (`GetSystemPowerStatus`).
   - Automatically transitions to `Quiet` mode when unplugged on battery, silencing loud fans and extending battery runtime.
   - Seamlessly restores preferred AC profile (`Balanced`/`Performance`) upon reconnecting AC.
   - Can be toggled on/off in the Tray menu.

4. **Hardware Safety & Watchdog:**
   - Standalone hardware watchdog process (`tcc-watchdog.exe`) launched detached via WMI `Win32_Process.Create`.
   - Survives process tree kills (`taskkill /T`, Task Manager). Restores Balanced profile within ~12s if the main app crashes or freezes.
   - Dual-layer fail-safe: user-configurable debounce threshold (default 85°C GPU / 95°C CPU with 8s spike filter) + un-bypassable emergency fail-safe at 100°C CPU / 90°C GPU.

5. **Direct NVIDIA NVML GPU Temperature:**
   - Directly queries the NVIDIA driver via NVML, permanently fixing the upstream Dell WMI 2–3°C idle reading bug.
   - Dell WMI Sensor 6 retained as a seamless fallback.

6. **Max Efficiency & Zero Wakeup Stutter:**
   - Idle CPU reduced from **0.59% down to 0.19%**.
   - Wakeups reduced from **21.5/s down to 10.5/s** (active window) and **~2/s** (minimized to tray).
   - Removed high-frequency animation timers. Gauges update directly on arrival without CPU burn.

7. **One-Click Bug Report Diagnostics:**
   - Bundles system specs, WMI dump, and logs into a privacy-redacted zip and pre-populates a GitHub issue.

---

## Artifact Checksums (SHA-256)

```
E70844A3D84B2C948A525676601E33EB94213B56FBAEB47693757BD1F4DB78E3  dist/tcc-g15-installer-1.8.0.exe
1C31143899D93D2E1F17EDE88B31E6A0E5AA8C420BC8A9153A462175939CD856  dist/tcc-g15/tcc-g15.exe
BE4279719DE95196E3C7B578F84D75F22697047AB1FEAEF9490434E262D7E543  dist/tcc-g15/tcc-watchdog.exe
```

---

## Verification & Test Results
- **Unit Test Suite:** 14/14 tests passing (`pytest tests/`)
- **Regression Suite:** 12/12 assertions passing (`tools/check_env.py`)
- **Real Hardware Validation:** Tested on Dell G15 5530 (i7-13650HX, RTX 4060 Laptop GPU, BIOS 1.36.0, Windows 11 Pro 26300).
