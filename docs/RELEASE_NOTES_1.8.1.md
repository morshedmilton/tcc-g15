# Thermal Control Center (TCC-G15) v1.8.1 Release Notes

**Release Date:** 2026-11-04  
**Integrity, Safety Invariant & CI Remediation Release**  

---

## 🚀 Key Improvements & Bug Fixes

1. **GitHub Actions CI Activation on `main` Branch (`DEF-001`):**
   - Fixed workflow trigger configuration in `.github/workflows/ci.yml` to execute on pushes and pull requests targeting `main`.
   - Resolves the issue where CI was previously configured for `master` and never executed on the actual default branch.

2. **Hardware Whitelist Reconciliation (`DEF-002`):**
   - Added `Dell G16 7630` and `Alienware m15 R7` to `SUPPORTED_MODELS` in `src/Backend/DetectHardware.py`.
   - Synchronized documentation table in `README.md` to achieve 100% parity with code whitelist.
   - Verified by unit tests.

3. **Automated Safety Invariant INV-1 Regression Test (`DEF-003`):**
   - Implemented automated regression test in `tests/test_safety_and_failsafe.py` verifying that the 100°C CPU / 90°C GPU emergency fail-safe override trips to `G_Mode` even if the user has disabled the soft fail-safe toggle in the UI.

4. **Repository Cleanliness & Log Exclusion (`DEF-004`):**
   - Untracked 34 runtime debug logs, PID files, and temporary artifacts from the git index.
   - Expanded `.gitignore` with strict rules for runtime, restore, and scratch files.

5. **Deterministic Dependencies & Supply Chain Hygiene (`DEF-005`):**
   - Pinned exact production runtime dependency versions in `requirements.txt`.
   - Created `requirements-dev.txt` for development, linting, and testing frameworks.

---

## 🔒 Cryptographic Checksums (SHA-256)

| Distribution | File Name | Size | SHA-256 Checksum |
|---|---|---|---|
| **Windows Installer** | `tcc-g15-installer-1.8.1.exe` | ~43.0 MB | `1dd982f0591d4600556b8d9c58cb38e304789fed32c93282aa20b1cd5621c8d5` |
| **Portable Zip** | `tcc-g15-portable-1.8.1.zip` | ~56.7 MB | `655a166df74e9946ea4f20e22dbfbf7047b81a76ddd320efba1fdb780e3882ad` |

### Verification (PowerShell)
```powershell
# Verify Installer
(Get-FileHash .\tcc-g15-installer-1.8.1.exe -Algorithm SHA256).Hash -eq "1DD982F0591D4600556B8D9C58CB38E304789FED32C93282AA20B1CD5621C8D5"

# Verify Portable Zip
(Get-FileHash .\tcc-g15-portable-1.8.1.zip -Algorithm SHA256).Hash -eq "655A166DF74E9946EA4F20E22DBFBF7047B81A76DDD320EFBA1FDB780E3882AD"
```
