# Thermal Control Center (TCC-G15) v1.8.3 Release Notes

**Release Date:** 2026-11-04  
**Performance, Decoupled Telemetry Engine & UI Fluidity**  

---

## 🚀 Key Improvements & Architecture Hardening

1. **Decoupled Background Telemetry Engine (`OPP-001` / ADR-003):**
   - In previous builds, synchronous Dell ACPI WMI queries and NVIDIA NVML driver polls were executed directly on the Qt GUI Main Thread every 2 seconds.
   - When the laptop was under 100% CPU/GPU gaming or rendering load, WMI bus latency caused noticeable micro-stutters during window dragging and button hover interactions.
   - Implemented `TelemetryWorker` running on a dedicated secondary `QtCore.QThread`. WMI and NVML queries now occur completely decoupled from the main thread, dropping UI thread latency to < 1 ms per tick and ensuring 100% fluid 60+ FPS UI responsiveness.

2. **Strongly-Typed Immutable Telemetry Snapshot (`OPP-005`):**
   - Introduced `TelemetrySnapshot` frozen dataclass DTO for thread-safe cross-apartment sensor communication.
   - Telemetry data is emitted atomically via Qt queued signals/slots (`telemetryReady`), preventing any shared-memory race conditions.

3. **Sensor Fallback & Safety Preservation:**
   - Preserves complete NVML primary driver reading with automatic fallback to Dell ACPI WMI sensor.
   - Fail-safe timeout guard (INV-2) guarantees that if background telemetry ever stalls or goes silent for > 60 seconds, emergency cooling mode (G-Mode) is automatically engaged.

4. **Multi-level Unit & Regression Test Suite:**
   - Added 6 new unit tests in `tests/test_telemetry_worker.py` covering worker polling, signal dispatch, NVML fallback, and clean QThread lifecycle teardown.
   - Total test suite expanded to **30 automated tests passing with 100% green rate**.

---

## 🔒 Cryptographic Checksums (SHA-256)

| Distribution | File Name | Size | SHA-256 Checksum |
|---|---|---|---|
| **Windows Installer** | `tcc-g15-installer-1.8.3.exe` | 45,139,561 bytes (43.0 MB) | `22E0DAB378D1562E7DC436DEF8C3C224AB9CD2871740F4F006A2FD2E14F6E771` |
| **Portable Zip** | `tcc-g15-portable-1.8.3.zip` | 59,479,615 bytes (56.7 MB) | `82E5BF2BBABBBCD063281F6FF5D5D5A4C6AF7A1BC438EED29E94F9CA41BC5E05` |
| **CycloneDX SBOM** | `tcc-g15-sbom.json` | 6,136 bytes (6.0 KB) | `CBB837FCBA8535451A0247EF2C614032100B5CB037F1C74769CFFDE454833FFF` |
