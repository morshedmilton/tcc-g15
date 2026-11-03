# Contributing to tcc-g15 (Dell G15 5530 Fork)

Thank you for your interest in contributing! This project is an open-source, ultra-efficient thermal control utility specifically tailored for the Dell G15 5530 (with support for compatible Dell G15 models).

## Core Principles

1. **Hardware Safety First:**
   - Under no circumstances will changes be accepted that bypass fail-safes, execute raw EC writes, modify CPU voltages, or flash firmware.
   - All thermal control must use verified WMI method calls (`AWCCWmiMethodFunction`).
   - The hardware watchdog and failsafe mechanisms must never be weakened.

2. **Clean-Room & License Hygiene:**
   - The project is licensed under **GPL-3.0**.
   - Original research and copyright by AlexIII is attributed and respected.
   - **Do NOT** decompile Dell/Alienware proprietary binaries and copy code or assets into this repository. All interfaces are reverse-engineered via public WMI observation and clean-room implementation.

3. **Evidence Over Assumptions:**
   - Every performance claim (CPU%, RAM, wakeups, temperatures) must be verified with measurements.

## Development Workflow

1. Fork the repository and create a feature branch (`git checkout -b feat/my-feature`).
2. Set up virtual environment and install dependencies:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Run the unit tests and regression suite:
   ```powershell
   pytest tests/ -v
   python tools/check_env.py
   ```
4. Follow Conventional Commits format (e.g. `feat: add battery profile automation`, `fix: handle invalid sensor reading`).
5. Open a Pull Request using the PR template.
