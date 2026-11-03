# TCC-G15 Technical Research & Intelligence Dossier

**Status:** Validated for Cycle 001  
**Author:** Research & Competitive Intel Role (hat)  
**Last Updated:** 2026-11-04  

---

## 1. Source Records (`SRC-###`)

### `SRC-001`: Dell AWCC ACPI WMI Interface Architecture
- **Subject:** Dell AWCC WMI Method Function (`AWCCWmiMethodFunction` under namespace `root\WMI`).
- **Primary References:** Linux kernel `drivers/platform/x86/dell/alienware-wmi.c`, Dell SMBIOS/ACPI tables.
- **Findings:**
  - Method `Thermal_Information` uses packed integer arguments: bits 8–15 hold sensor/fan index, bits 0–7 hold sub-function (e.g. 4 for sensor temp, 5 for RPM, 6 for RPM percentage).
  - Modern Dell G15 models (starting with G15 5530 and G16 7630, BIOS 1.36.0+) use the USTT (Unified System Thermal Table) firmware protocol.
  - Older Dell models accept mode codes `0x97` (Balanced), `0x98` (Performance), `0x96` (Quiet). Modern USTT models reject those with error codes and only accept `0xA0` (Balanced), `0xA1` (Performance), `0xA3` (Quiet), and `0xAB` (G-Mode).
  - `Custom` mode `0x0` enables manual fan speed offset control via method `Thermal_Control`.
- **Reliability:** `FACT` (verified through kernel source and physical hardware probing on this machine).

### `SRC-002`: NVIDIA NVML API Telemetry vs Dell WMI Sensor
- **Subject:** NVIDIA Management Library (`pynvml` / `nvidia-ml-py`).
- **Findings:**
  - On laptops with NVIDIA RTX 30/40 series GPUs, Dell WMI Sensor 6 frequently reports a frozen or bogus 2–3°C reading when the dGPU is in ultra-low power state (D3cold).
  - Calling `nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)` accesses the GPU driver thermal diode directly, providing real-time accurate readings (e.g., 40–80°C).
  - If the dGPU powers down completely or driver restarts occur, NVML gracefully raises exceptions or returns `None`, allowing clean fallback to WMI Sensor 6 without crashing the GUI.
- **Reliability:** `FACT` (verified in `GpuTemp.py` and benchmarked).

### `SRC-003`: Upstream Comparison (`AlexIII/tcc-g15`)
- **Subject:** Diff between upstream repository (`AlexIII/tcc-g15`) and this fork.
- **Findings:**
  - Upstream `1.6.4` (January 2025) supports only 3 modes on older G15 models; on G15 5530 it fails because it uses hardcoded legacy mode IDs (`0x97`, `0x96`, `0x98`).
  - Upstream lacks a watchdog process; if the app crashes, fans stay frozen at whatever offset was last written.
  - Upstream lacks battery automation (`GetSystemPowerStatus`).
  - Upstream uses an opaque Win32 dialog interface with high GUI wakeup frequency (~21 wakeups/sec).
  - This fork introduces: 5 full USTT modes, DWM Acrylic Liquid Glass UI, vector tachometer gauges, detached watchdog, battery power-state detection, NVML direct driver telemetry, and privacy-redacted diagnostics.
- **Reliability:** `FACT` (verified by direct code audit and upstream tag comparison).

### `SRC-004`: Windows DWM System Backdrop API
- **Subject:** Windows 11 Desktop Window Manager Backdrop attribute (`DWMWA_SYSTEMBACKDROP_TYPE = 38`).
- **Findings:**
  - Value 1 = Auto, Value 2 = None, Value 3 = Acrylic, Value 4 = Mica, Value 5 = Tabbed.
  - Value 3 (`DWMSBT_ACRYLIC`) provides translucent frosted glass dynamically blurring background content behind the window.
  - Requires `DwmExtendFrameIntoClientArea` with negative margins (`MARGINS(-1, -1, -1, -1)`) and translucent Qt background (`setAttribute(Qt.WA_TranslucentBackground)`).
- **Reliability:** `FACT` (verified in `AppGUI.py:applyWindowsGlassAndDarkTheme`).

### `SRC-005`: Multi-Threaded COM Initialization
- **Subject:** Windows COM Apartment initialization (`pythoncom.CoInitialize()`).
- **Findings:**
  - Calling WMI from background threads without `CoInitialize()` raises `pywintypes.com_error: -2147221008 (CoInitialize has not been called)`.
  - Every secondary thread performing WMI operations (e.g. `DetectHardware` background query) must explicitly call `pythoncom.CoInitialize()`.
- **Reliability:** `FACT` (fixed in commit `9cee268` and verified by test `test_detect_hardware_thread_safety`).

---

## 2. Research Conclusions
All architectural assumptions are verified by source code and official vendor APIs. No unverified third-party libraries or speculative hooks are in use. Gate G1 exit criteria are met.
