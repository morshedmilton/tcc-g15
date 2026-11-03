# Thermal Control Center (TCC) — Dell G-Series & Alienware Edition

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Platform: Windows 10 / 11](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg?logo=windows)](https://microsoft.com/windows)
[![Python: 3.13 | PySide6](https://img.shields.io/badge/Python-3.13%20%7C%20PySide6-3776AB.svg?logo=python)](https://pyside.org)
[![Hardware: Dell G15 5530 Verified](https://img.shields.io/badge/Hardware-Dell%20G15%205530%20Verified-00FF66.svg)]()
[![Release: v1.8.0](https://img.shields.io/badge/Release-v1.8.0-yellow.svg)](https://github.com/morshedmilton/tcc-g15/releases)
[![Build Status: CI Passing](https://img.shields.io/badge/CI-Passing-brightgreen.svg)]()

A high-performance, liquid-efficient, open-source replacement for Alienware Command Center (AWCC). Engineered specifically for Dell G-series and Alienware gaming laptops with **true Windows 11 DWM Acrylic frosted glass**, a **futuristic Cyberpunk HUD**, and direct hardware-level thermal management.

---

> ### 📜 Attribution & Open Source Heritage
> This project is an independent evolution of **[tcc-g15](https://github.com/AlexIII/tcc-g15)** originally created by **[AlexIII](https://github.com/AlexIII)**.  
> We express our immense gratitude to AlexIII for the original research, reverse engineering of Dell's WMI thermal interface, and initial implementation.
>
> In accordance with the **GNU General Public License v3.0**, this project is published as a fully open-source, independent tool to provide ongoing active development, Dell G15 5530 USTT firmware profiles, NVIDIA NVML telemetry, safety watchdogs, smart battery automation, and a modern liquid glass interface.
> - **Original Project:** [AlexIII/tcc-g15](https://github.com/AlexIII/tcc-g15) (Copyright © 2022–2025 AlexIII)
> - **Current Fork & Maintenance:** [morshedmilton/tcc-g15](https://github.com/morshedmilton/tcc-g15) (Copyright © 2026 Md. Morshed Milton and contributors)
> - **License:** GNU General Public License v3.0 (GPL-3.0)

---

## 📸 Interface Preview

<!-- SCREENSHOT_PLACEHOLDER_START -->
![Thermal Control Center Preview](docs/assets/screenshot.png)
*Figure: Futuristic Cyberpunk HUD with 25° skewed tachometer gauges and real-time Windows 11 DWM Acrylic frosted glass translucency.*
<!-- SCREENSHOT_PLACEHOLDER_END -->

> **Note for Users:** When the application runs on your system, the background is a translucent frosted glass pane that dynamically blurs and shifts with whatever wallpaper, application, or browser is beneath it!

---

## 💻 Supported Laptop Models

This software interacts directly with Dell's thermal and fan firmware tables via the `AWCCWmiMethodFunction` interface.

### 🟢 Tier 1: Officially Verified & Tested
| Model | CPU Architecture | Dedicated GPU | BIOS Version Tested | Status |
|---|---|---|---|---|
| **Dell G15 5530** | Intel 13th Gen Core (i7-13650HX, i5-13450HX, i9-13900HX) | RTX 4050 / RTX 4060 / RTX 4070 Laptop | 1.36.0+ | **100% Verified** |

### 🟡 Tier 2: Community Verified (Fully Compatible)
These models share Dell's USTT / Legacy thermal interfaces and fan sensor maps:
- **Dell G15 5520** (Intel Core 12th Gen)
- **Dell G15 5525** (AMD Ryzen 6000 Series)
- **Dell G15 5515** (AMD Ryzen 5000 Series)
- **Dell G15 5511** (Intel Core 11th Gen)
- **Dell G15 5535** (AMD Ryzen 7000 Series)
- **Dell G16 7630** (Intel Core 13th Gen chassis)
- **Dell Alienware m16 R1 / m15 R7**

### ⚪ Tier 3: Universal Fallback
For any other Dell G-series, Inspiron Gaming, or Alienware laptop, launch with:
```powershell
$env:TCC_ALLOW_UNSUPPORTED="1"
.\tcc-g15.exe
```
*(If it works on your model, please open an issue so we can add it to Tier 1/2!)*

---

## 🚀 Key Features

### 1. 🪟 True Windows 11 DWM Acrylic Liquid Glass
- Native integration with Windows 11 Desktop Window Manager (`DWMWA_SYSTEMBACKDROP_TYPE = 3` + `DwmExtendFrameIntoClientArea`).
- Translucent frosted glass effect that dynamically blends and blurs whatever is behind the window.
- Sleek ultra-compact dimensions (**~492 × 165 px**), restoring the beloved compact footprint of classic utilities without unnecessary bloat.

### 2. ⚡ 5 Full Hardware Thermal Profiles
Unlock all 5 firmware profiles supported by Dell G15 5530 USTT architecture:
- **Custom (`0x0`):** Full manual control over fan offsets.
- **Balanced (`0xA0`):** Everyday optimal balance between acoustics and thermals.
- **Performance (`0xA1`):** Aggressive fan curves for heavy workloads.
- **Quiet (`0xA3`):** Strict acoustic limits for silent operation during meetings or library use.
- **G-Mode // Overdrive (`0xAB`):** Max fan RPM override (up to 5500 RPM) for peak gaming sessions.

### 3. 🎯 Direct NVIDIA NVML Driver Telemetry
- Reads GPU temperature directly from the official NVIDIA NVML driver API, completely eliminating Dell WMI's notorious "2–3°C idle reading" bug.
- Dell WMI Sensor 6 is retained as a zero-downtime automatic fallback.

### 4. 🔋 Smart Battery Automation
- Uses Win32 power management hooks (`GetSystemPowerStatus`) to detect AC vs Battery power in real time.
- Automatically transitions to **Quiet** mode on battery to eliminate fan noise and maximize battery life, restoring your preferred performance profile when plugged back into AC.

### 5. 🛡️ Dual-Layer Safety & Detached Watchdog
Hardware safety is non-negotiable when controlling thermal firmware:
- **Spike Debouncing:** 8-second debounce window prevents transient thermal spikes from triggering unnecessary fan spin-ups.
- **Un-bypassable Emergency Trip:** Immediate fail-safe override if CPU exceeds 100°C or GPU exceeds 90°C.
- **Detached Watchdog Process (`tcc-watchdog.exe`):** A lightweight background watchdog launched independently via WMI. If the main application crashes, hangs, or is terminated by Task Manager, the watchdog automatically restores **Balanced** mode.

### 6. 🪶 Extreme Efficiency (Zero Interruptions)
- Pure vector `QPainter` rendering with zero continuous animation loops.
- Idle CPU consumption: **< 0.20%**.
- RAM consumption: **~26 MB**.
- Wakeup rate: minimal (~2 wakeups/sec minimized to tray).

---

## 📥 Download & Installation

### Option A: Windows Installer (Recommended)
1. Download **`tcc-g15-installer-1.8.0.exe`** from the [Latest Release](https://github.com/morshedmilton/tcc-g15/releases).
2. Run the installer. It configures the application files, tray icon, and optional startup task.
3. Launch **Thermal Control Center** from the Start Menu or Desktop shortcut.

### Option B: Standalone Portable Exe
1. Download the portable zip containing `tcc-g15.exe` and `tcc-watchdog.exe`.
2. Extract to any folder (e.g. `C:\Tools\tcc-g15\`).
3. Right-click `tcc-g15.exe` and select **Run as Administrator** (required for Dell WMI access).

### Checksums (SHA-256)
```text
846AC5928441A2716A3F8232DDA3A13CD6CF4853F8552542D7241636CCE5465C *tcc-g15-installer-1.8.0.exe
8BB74947036CC4B00E98EE18391FA800FF1FEB9CC32D107995E8A1D775857AB4 *tcc-g15/tcc-g15.exe
BE4279719DE95196E3C7B578F84D75F22697047AB1FEAEF9490434E262D7E543 *tcc-g15/tcc-watchdog.exe
```

---

## 🛠️ Building from Source

```powershell
# 1. Clone repository
git clone https://github.com/morshedmilton/tcc-g15.git
cd tcc-g15

# 2. Create virtual environment and install dependencies
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Run unit test suite (hardware-free mock WMI)
pytest tests/ -v

# 4. Run application
python src/tcc-g15.py
```

To build standalone executables and the Inno Setup installer:
```powershell
# Build executables with PyInstaller
pyinstaller tcc-g15.spec --noconfirm
pyinstaller tcc-watchdog.spec --noconfirm

# Compile installer (requires Inno Setup 6)
iscc installer/tcc-g15-setup.iss
```

---

## ❓ Frequently Asked Questions

<details>
<summary><b>Why does the app require Administrator privileges?</b></summary>
Dell's ACPI thermal table methods live inside the root\WMI namespace (specifically the AWCCWmiMethodFunction class). Microsoft Windows restricts access to low-level hardware ACPI/WMI methods to Elevated (Administrator) tokens for security.
</details>

<details>
<summary><b>Do I need Alienware Command Center (AWCC) installed?</b></summary>
<b>No!</b> This application communicates directly with Dell's BIOS/firmware WMI interface. You can completely uninstall AWCC, Alienware OC Controls, and AWCC Background Services.
</details>

<details>
<summary><b>Why do the fans still spin at ~3000 RPM when set to 0%?</b></summary>
Dell's embedded controller (EC) and BIOS maintain an internal thermal floor (~3000 RPM / 70% floor on modern G15 models). The slider provides a positive offset over the firmware base curve; it will not let you turn fans completely off when the hardware needs cooling.
</details>

---

## 🤝 Contributing

Contributions are welcome! Whether you are reporting compatibility on a new laptop model, fixing a bug, or improving documentation:
1. Check [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.
2. Open an issue or submit a pull request.
3. Ensure `pytest tests/ -v` and `python tools/check_env.py` pass.

---

## ⚖️ License & Trademarks

- **License:** Distributed under the terms of the **[GNU General Public License v3.0](LICENSE)**.
- **Trademarks:** This project is an independent, unofficial community tool. It is not affiliated with, endorsed by, or associated with Dell Technologies, Alienware, or Microsoft Corporation. All registered trademarks belong to their respective owners.
