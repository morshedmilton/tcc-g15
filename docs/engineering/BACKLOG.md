# TCC-G15 Evolution Backlog & Opportunity Register

Prioritized engineering backlog. Every candidate is scored using:
$$\text{Score} = \frac{\text{Impact} \times \text{Confidence} \times \text{UserValue}}{\text{Effort} \times \text{Risk}}$$
where each factor is an integer from 1 to 5.

---

## 1. Candidate Register

| ID | Class | Title | Imp | Conf | Val | Eff | Risk | Score | Priority | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| `DEF-001` | Bug | Fix CI workflow to trigger on `main` & PRs to `main` | 5 | 5 | 5 | 1 | 1 | **125.0** | **P0** | **VERIFIED (Cycle 1)** |
| `DEF-002` | Compat | Reconcile hardware whitelist with README Tier 2 models | 5 | 5 | 5 | 1 | 1 | **125.0** | **P0** | **VERIFIED (Cycle 1)** |
| `DEF-003` | Safety | Implement automated unit test for INV-1 hard fail-safe trip | 5 | 5 | 5 | 1 | 1 | **125.0** | **P0** | **VERIFIED (Cycle 1)** |
| `DEF-004` | Repo | Untrack temporary debug artifacts & expand `.gitignore` | 4 | 5 | 4 | 1 | 1 | **80.0** | **P1** | **VERIFIED (Cycle 1)** |
| `DEF-005` | Supply | Pin production dependencies & separate test/dev dependencies | 4 | 5 | 4 | 1 | 1 | **80.0** | **P1** | **VERIFIED (Cycle 1)** |
| `OPP-002` | Reliability | Watchdog heartbeat resilience across sleep/standby + GUI resurrection | 5 | 5 | 5 | 2 | 1 | **62.5** | **P1** | **VERIFIED (Cycle 2)** |
| `OPP-003` | Safety | Thermal mode application retry on transient WMI communication failure | 4 | 5 | 4 | 2 | 1 | **40.0** | **P1** | **VERIFIED (Cycle 2)** |
| `OPP-004` | Supply | Automated machine-readable SBOM (CycloneDX) in build pipeline | 4 | 5 | 4 | 2 | 1 | **40.0** | **P1** | **VERIFIED (Cycle 2)** |
| `OPP-001` | Perf | Background worker thread for telemetry polling (decouple WMI from GUI thread) | 4 | 5 | 5 | 2 | 1 | **50.0** | **P1** | **VERIFIED (Cycle 3)** |
| `OPP-005` | Arch | Strongly-typed `TelemetrySnapshot` immutable data transfer object | 4 | 5 | 4 | 1 | 1 | **80.0** | **P1** | **VERIFIED (Cycle 3)** |
| `OPP-006` | Obs | Real-time session telemetry export to CSV/JSON for thermal profiling | 4 | 5 | 4 | 2 | 1 | **40.0** | **P1** | **VERIFIED (Cycle 4)** |
| `OPP-007` | Safety | Thermal throttling excursion metrics and sustained overload warnings | 3 | 4 | 4 | 2 | 1 | **24.0** | **P2** | BACKLOG (Cycle 5) |

---

## 2. Cycle 4 Scope (Current)

In accordance with Master Directive §5 Phase 3:
1. **`OPP-006` (P1 - Observability & Diagnostics):** Real-time session telemetry export to standard RFC 4180 CSV, bounded log rotation (max 5 sessions, max 10MB per file), tray menu controls, and diagnostics bug report integration.

---

## 3. Rejected Register

- **Rewrite in Rust / C++:** Rejected per Master Directive §2 (Prime Directive 5). Python 3.13 + PySide6 uses ~0.20% CPU and 26 MB RAM. No performance justification for rewrite.
- **Support for non-Dell hardware:** Rejected. The core purpose of TCC is Dell ACPI WMI control (`AWCCWmiMethodFunction`).
