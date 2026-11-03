# HARDWARE.md — Machine Hardware & WMI Survey

**Target System:** Dell G15 5530 (Verified on real hardware)  
**Date of Survey:** 2026-11-03  
**Status:** Auto-detected via read-only WMI / CIM queries

---

## 1. System Specifications

| Component | Specification |
|---|---|
| **System Model** | Dell G15 5530 |
| **Manufacturer** | Dell Inc. |
| **Operating System** | Microsoft Windows 11 Pro (10.0.26300 Build 26300) |
| **BIOS Version** | 1.36.0 (Release: 2026-08-26) |
| **CPU** | 13th Gen Intel(R) Core(TM) i7-13650HX (14 cores: 6 P-cores, 8 E-cores / 20 threads) |
| **RAM** | 16.0 GB DDR5 |
| **Integrated GPU (iGPU)** | Intel(R) UHD Graphics (Driver: 32.0.101.7088) |
| **Discrete GPU (dGPU)** | NVIDIA GeForce RTX 4060 Laptop GPU (Driver: 32.0.16.2101) |

---

## 2. WMI Architecture & Classes

### Namespaces:
- `root/wmi`: Contains Dell's low-level hardware interface class `AWCCWmiMethodFunction`.
- `root/cimv2`: Standard Windows CIM classes.

### AWCC WMI Interface (`root/wmi` -> `AWCCWmiMethodFunction`):
The class provides 34 method entry points. The critical methods utilized by `tcc-g15` include:

| Method | Role in `tcc-g15` | Status on G15 5530 |
|---|---|---|
| `Thermal_Information` | Reads temperatures, fan RPM, fan percentage, thermal profiles | Fully Functional |
| `Thermal_Control` | Sets thermal profile modes (Balanced, Performance, Quiet, G-Mode, Custom) and fan speeds | Fully Functional |
| `GetFanSensors` | Maps fan indices to temperature sensor indices | Functional |
| `GameShiftStatus` | G-key toggle status detection | Functional |

### Sensor Mapping:
- **CPU Fan (Index 50):** Mapped to Sensor 1 (~45°C - 85°C, up to ~5500 RPM max).
- **GPU Fan (Index 51):** Mapped to Sensor 6 (~40°C - 80°C, up to ~5500 RPM max).
- **GPU Temp Source:** Dual capability — NVIDIA NVML (direct driver reading via `pynvml`/NVML DLL) as primary, with Dell WMI Sensor 6 as fallback. Avoids the 2°C/3°C low-reading anomaly seen on sleep/idle.

### Supported USTT Thermal Profiles on G15 5530:
- **Balanced (0xA0):** Standard daily operation (Dell default).
- **Performance (0xA1):** Aggressive fan profile & higher power limits.
- **Quiet (0xA3):** Acoustic-optimized low-noise profile.
- **G-Mode (0xAB):** Game Shift max-cooling profile (100% fans, High Performance mode).
- **Custom (0x00):** Direct manual fan duty/RPM control.
