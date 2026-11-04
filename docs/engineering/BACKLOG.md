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
| `OPP-007` | Safety | Thermal throttling excursion metrics and sustained overload warnings | 3 | 4 | 4 | 2 | 1 | **24.0** | **P2** | **VERIFIED (Cycle 5)** |
| `DEF-008` | Safety | Unconditional INV-1 Hard Fail-Safe Supremacy in OPP-008 switching logic | 5 | 5 | 5 | 1 | 1 | **125.0** | **P0** | **FROZEN (Cycle 6)** |
| `DEF-006` | Privacy | Diagnostics PII Redaction for UserName, PrimaryOwnerName, DNSHostName | 4 | 5 | 4 | 1 | 1 | **80.0** | **P1** | **FROZEN (Cycle 6)** |
| `DEF-007` | Supply | Promote `psutil==7.2.2` to production `requirements.txt` | 4 | 5 | 4 | 1 | 1 | **80.0** | **P1** | **FROZEN (Cycle 6)** |
| `DEF-009` | Arch | Dedicated QThread and Qt Signal/Slot COM apartment isolation | 4 | 5 | 4 | 1 | 1 | **80.0** | **P1** | **FROZEN (Cycle 6)** |
| `OPP-008` | Feature | Process-Aware Automatic Thermal Profile Switching with Custom Rules & 18 Presets | 5 | 5 | 5 | 3 | 1 | **41.7** | **P1** | **FROZEN (Cycle 6)** |

---

## 2. Cycle Scope History & Active Commitments

- **Cycle 1 (v1.8.1):** Foundational integrity & CI automation (`DEF-001` - `DEF-005`).
- **Cycle 2 (v1.8.2):** High-reliability watchdog heartbeat & SBOM generation (`OPP-002`, `OPP-003`, `OPP-004`).
- **Cycle 3 (v1.8.3):** Background telemetry polling worker & strongly-typed DTO (`OPP-001`, `OPP-005`).
- **Cycle 4 (v1.8.4):** Real-time session telemetry logging & bug report integration (`OPP-006`).
- **Cycle 5 (v1.8.5):** Session thermal analytics engine, tray peak indicators, and proactive overload advisories (`OPP-007`).
- **Cycle 6 (v1.8.6 - FROZEN SCOPE):**
  - **Prime Scope:** `OPP-008` (Process-Aware Automatic Thermal Profile Switching, Custom Rules, 18 Game/App Presets, 4s exit debounce hysteresis, Cooling Severity Priority Matrix).
  - **Safety & Invariant Fixes:**
    - `DEF-008` (P0): Unconditional INV-1 Hard Fail-Safe Supremacy in OPP-008 switching logic.
    - `DEF-006` (P1): Diagnostics PII Redaction for `UserName`, `PrimaryOwnerName`, and `DNSHostName`.
    - `DEF-007` (P1): Promote `psutil==7.2.2` to production `requirements.txt`.
    - `DEF-009` (P1): Dedicated QThread and Qt Signal/Slot COM apartment isolation.

---

## 3. Rejected Register

- **Rewrite in Rust / C++:** Rejected per Master Directive §2 (Prime Directive 5). Python 3.13 + PySide6 uses ~0.20% CPU and 26 MB RAM. No performance justification for rewrite.
- **Support for non-Dell hardware:** Rejected. The core purpose of TCC is Dell ACPI WMI control (`AWCCWmiMethodFunction`).
- **Synchronous WMI process querying (`Win32_Process`):** Rejected due to 1,743ms latency per scan and high CPU spike in `WmiPrvSE.exe`, which severely blocks execution loops.
- **WMI Event Consumer (`__InstanceCreationEvent`):** Rejected due to 3–8% CPU overhead, Modern Standby (S0ix/S3) sleep/resume event drops, silent COM sink unregistration, and cross-apartment threading fragility.
- **Deep process inspection / memory access for protected game processes:** Rejected due to anti-cheat isolation (BattlEye, Easy Anti-Cheat, Riot Vanguard); only non-invasive basename matching via `psutil.process_iter(['name'])` from global NT kernel tables is permitted.
