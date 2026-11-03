# TCC-G15 Evolution Backlog & Opportunity Register

Prioritized engineering backlog. Every candidate is scored using:
$$\text{Score} = \frac{\text{Impact} \times \text{Confidence} \times \text{UserValue}}{\text{Effort} \times \text{Risk}}$$
where each factor is an integer from 1 to 5.

---

## 1. Candidate Register

| ID | Class | Title | Imp | Conf | Val | Eff | Risk | Score | Priority | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| `DEF-001` | Bug | Fix CI workflow to trigger on `main` & PRs to `main` | 5 | 5 | 5 | 1 | 1 | **125.0** | **P0** | **SCOPED (Cycle 1)** |
| `DEF-002` | Compat | Reconcile hardware whitelist (`DetectHardware.py`) with README Tier 2 models | 5 | 5 | 5 | 1 | 1 | **125.0** | **P0** | **SCOPED (Cycle 1)** |
| `DEF-003` | Safety | Implement automated unit test for INV-1 hard fail-safe trip | 5 | 5 | 5 | 1 | 1 | **125.0** | **P0** | **SCOPED (Cycle 1)** |
| `DEF-004` | Repo | Untrack temporary debug artifacts & expand `.gitignore` | 4 | 5 | 4 | 1 | 1 | **80.0** | **P1** | **SCOPED (Cycle 1)** |
| `DEF-005` | Supply | Pin production dependencies & separate test/dev dependencies | 4 | 5 | 4 | 1 | 1 | **80.0** | **P1** | **SCOPED (Cycle 1)** |
| `OPP-001` | Perf | Background worker thread for telemetry polling (decouple WMI from GUI thread) | 4 | 4 | 4 | 3 | 2 | **10.7** | **P2** | BACKLOG (Cycle 2) |
| `OPP-002` | Reliability | Watchdog heartbeat validation across system sleep/hibernate resume | 4 | 4 | 4 | 3 | 2 | **10.7** | **P2** | BACKLOG (Cycle 2) |
| `OPP-003` | Safety | WMI readback verification after thermal mode switch | 4 | 4 | 4 | 2 | 2 | **16.0** | **P2** | BACKLOG (Cycle 2) |
| `OPP-004` | Security | Generate machine-readable SBOM (CycloneDX / SPDX) in build pipeline | 3 | 5 | 3 | 2 | 1 | **22.5** | **P2** | BACKLOG (Cycle 2) |

---

## 2. Cycle 1 Scope (Current)

In accordance with Master Directive §5 Phase 3 (all open P0s + up to 5 P1/P2 items):
1. **`DEF-001` (P0):** Fix `.github/workflows/ci.yml` trigger branches to include `main` and PRs targeting `main`.
2. **`DEF-002` (P0):** Add missing models (`G16 7630`, `m15 R7`) to `SUPPORTED_MODELS` in `DetectHardware.py`, synchronize with README, and add unit test.
3. **`DEF-003` (P0):** Add explicit unit test in `tests/test_safety_and_failsafe.py` validating that the 100°C CPU / 90°C GPU emergency trip triggers even when `_failsafeOn == False`.
4. **`DEF-004` (P1):** Remove 44 tracked temporary log/pid/txt/png files from git index, keep necessary local files, and add strict rules to `.gitignore`.
5. **`DEF-005` (P1):** Pin exact runtime dependencies in `requirements.txt` and create `requirements-dev.txt` for development/testing tools.

---

## 3. Rejected Register

*(Candidates evaluated and rejected with rationale)*
- **Rewrite in Rust / C++:** Rejected per Master Directive §2 (Prime Directive 5). Python 3.13 + PySide6 uses ~0.20% CPU and 26 MB RAM. No performance justification for rewrite.
- **Support for non-Dell hardware:** Rejected. The core purpose of TCC is Dell ACPI WMI control (`AWCCWmiMethodFunction`).
