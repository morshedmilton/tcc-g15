# WMI_MAP.md — what the G15 5530 actually exposes

**Machine:** Dell G15 5530 · i7-13650HX · RTX 4060 Laptop + Intel UHD · 15.7 GB RAM · Windows 11 Pro · BIOS 1.36.0 · NVIDIA driver 621.01
**Produced by:** `tools/wmi_survey.py` (read-only) + `tools/hwprobe.py` (elevated, read-only) + `nvidia-smi`/NVML
**Raw data:** `docs/WMI_MAP.json`, `tcc-g15-research/hwprobe-5530.json`

## The AWCC interface

`root\WMI` → **`AWCCWmiMethodFunction`** — present, **34 methods**, provided by firmware/ACPI, **not by the AWCC app** (AWCC is not installed on this machine and the class still works).

Methods relevant to us (ids from the class schema):

| WmiMethodId | Method | Use |
|---|---|---|
| 19 | `GetFanSensors` | fan → related sensor mapping |
| 20 | `Thermal_Information` | temps, fan RPM, (RPM% unsupported here) |
| 21 | `Thermal_Control` | set thermal mode, set fan speed offset |
| 26 | `SystemInformation` | — |
| 28 | `PowerInformation` | — |
| 37 | `GameShiftStatus` | the "real" G-mode switch that upstream declined to use |
| 35/33/34 | `ReadChassisColor` / `ReadTotalofGPIOs` / `ReadGPIOpPinStatus` | lighting — **unverified on 5530** |
| 13/14/22/23/24/25 | OC report / OC UI / BIOS OC / Memory OC | **out of scope** — BIOS writes, excluded by safety rule 2c |

## Verified sensor/fan map on this exact board

```
fan 50 → sensor 1   CPU   ~66 °C   3826 rpm
fan 51 → sensor 6   GPU   ~53 °C   4013 rpm
live sensors       : 1 and 6 only (documented range is 1–48)
GetFanRPMPercent   : returns -2  → unsupported on this board
```

## Capability matrix vs AWCC

| Capability | AWCC | upstream tcc-g15 | On 5530, verified | Verdict |
|---|---|---|---|---|
| Thermal mode: Balanced / Custom / G | ✅ | ✅ | ✅ app runs, mode applies | **done** |
| Thermal mode: Quiet / Performance / FullSpeed | ✅ | ❌ | enum exists (`150/152/153`, USTT `160–165`) but never exercised here | **feasible — needs a hardware test** |
| Fan RPM read | ✅ | ✅ | ✅ 3826 / 4013 rpm | **done** |
| Fan speed set (offset over BIOS curve) | ✅ | ✅ | ✅ (BIOS floor ≈70 % / ≥3000 rpm) | **done, floor must be surfaced in UI** |
| Fan RPM percent read | ✅ | partial | ❌ returns -2 | **not exposed — stop pretending it works** |
| Per-fan temperature | ✅ | ✅ (first related sensor only) | ✅ sensors 1 and 6 | **done** |
| CPU package / core temps | ✅ | ❌ | ❌ no MSR access without a kernel driver | **not exposed** (driver install = out of scope) |
| **Real GPU temperature** | ✅ | ⚠️ Dell WMI sensor (bogus 2–3 °C bug) | ✅ **NVML: 61 °C** (`nvidia-smi`, driver 621.01) | **feasible — strictly better than WMI** |
| GPU power draw | ✅ | ❌ | ✅ NVML: 22.9 W | **feasible** |
| GPU clocks / utilisation | ✅ | ❌ | ✅ NVML | **feasible** |
| Keyboard / chassis RGB | ✅ | ❌ | ⚠️ AWCC lighting methods exist, unverified, AlienFX not installed | **unverified — do not promise** |
| Power limits / TDP / CPU OC | ✅ | ❌ | methods exist (`BIOSOCControl`) | **excluded** — BIOS writes need explicit approval |
| AC / battery state | ✅ | ❌ | ✅ `Win32_Battery`, `BatteryStatus` | **feasible** |
| Sleep / resume awareness | ✅ | ❌ | ✅ Windows power events | **feasible** |
| Autostart | ✅ | ⚠️ Task Scheduler (flaky, upstream #49) | — | **replace** |
| Fan curve (temp → speed) | ✅ | ❌ | pure software on top of the offset API | **feasible** |

## Consequences for the design

1. **GPU temperature must come from NVML, not the Dell WMI sensor.** NVML answered instantly and plausibly (61 °C) while the WMI sensor is the known source of the 2–3 °C bug (#9). Keep WMI as fallback for non-NVIDIA machines.
2. **Do not surface "fan RPM %"** — this board returns -2.
3. **Quiet/Performance are plausible but unproven.** They must be tested once on hardware (with the fail-safe armed) before shipping, or be shipped behind a "experimental" label.
4. **Lighting and TDP/OC stay out of v1.** The methods exist; the risk and the verification cost do not pay for themselves yet.
5. Everything else the app needs (temps, RPM, mode, fan offset) is available and already proven on this machine.
