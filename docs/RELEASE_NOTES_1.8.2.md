# Thermal Control Center (TCC-G15) v1.8.2 Release Notes

**Release Date:** 2026-11-04  
**Reliability, Watchdog Sleep Resilience & Software Bill of Materials (SBOM)**  

---

## 🚀 Key Improvements & Architecture Hardening

1. **Watchdog Sleep & Standby Resilience (`OPP-002` / ADR-002):**
   - Implemented monotonic loop duration tracking (`time.monotonic()`) in `tcc-watchdog.exe`.
   - When the host operating system enters Modern Standby, S3 sleep, or lid closure, the watchdog detects the suspend event and automatically grants a grace period upon resume.
   - Prevents false-positive emergency trips and avoids premature watchdog process termination.

2. **Watchdog Auto-Resurrection in GUI (`OPP-002`):**
   - The main GUI now checks the process health of the detached watchdog during each periodic poll.
   - If the watchdog process ever exits or is killed unexpectedly, the GUI automatically restarts it, guaranteeing 100% continuous hardware protection for the laptop.

3. **Thermal Mode Application Retry (`OPP-003`):**
   - Hardened `AWCCWmiWrapper.ApplyThermalMode` with an automatic transient retry to handle brief ACPI bus contention gracefully before declaring a mode unsupported.

4. **Cryptographic Software Bill of Materials (CycloneDX SBOM) (`OPP-004`):**
   - Integrated automated generation of `tcc-g15-sbom.json` (CycloneDX v1.6 specification) into the build and GitHub Actions CI pipelines, providing complete software supply-chain transparency.

---

## 🔒 Cryptographic Checksums (SHA-256)

| Distribution | File Name | Size | SHA-256 Checksum |
|---|---|---|---|
| **Windows Installer** | `tcc-g15-installer-1.8.2.exe` | 45,130,627 bytes (43.0 MB) | `3D69442EAE133329F9473F4BFA4222BD70D9C171765BD9591B7FD3B26911F22D` |
| **Portable Zip** | `tcc-g15-portable-1.8.2.zip` | 68,605,627 bytes (65.4 MB) | `6BA122BDF6FD4E038D589A771A024DED39FC3E08B209B055B06535A3B10955BF` |
| **CycloneDX SBOM** | `tcc-g15-sbom.json` | 6,136 bytes (6.0 KB) | `CD594333E572ACC79BD4D5BD172439D18B38B5701F16DB425FD62744D79E47A6` |
