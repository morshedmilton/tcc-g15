# ADR-005: Session Thermal Analytics, Sustained Saturation Advisory & Tray Peak Metrics

**Status:** Accepted  
**Date:** 2026-11-04  
**Author:** Multi-disciplinary Autonomous Engineering Organization  
**Supersedes / Relates to:** PRD Cycle 005 (`OPP-007`), ADR-003, ADR-004  

---

## 1. Context & Problem Statement

Users of Dell G15 systems running extended workloads (gaming, compiling, 3D rendering) experience thermal saturation that approaches the safety boundaries. Currently, TCC-G15 provides fail-safe trips when temperatures breach 95°C/100°C (CPU) or 85°C/90°C (GPU). However:
1. **Lack of Session Peak Visibility:** The system tray and GUI only display instantaneous temperatures. When a user minimizes a game to check temperatures, they often see lower idle temperatures because the load dropped, obscuring the peak thermal stress reached under load.
2. **No Early Advisory for Sustained Near-Critical Saturation:** When running in `Quiet` or `Balanced` modes, a CPU temperature hovering at 90°C–94°C for extended periods may cause severe thermal throttling before reaching the 95°C soft trip threshold.
3. **Diagnostics Lack Session Summary:** While Cycle 004 added raw session CSV logs, diagnosing performance issues requires quick aggregated metrics (Session Uptime, Peak CPU/GPU Temp, Cumulative High-Temp Excursion Seconds, Trip Count) without parsing entire CSV files.

---

## 2. Decision Drivers

- **Observability:** Immediate visibility of peak temperatures reached during the session directly in the system tray tooltip and bug report bundle.
- **Proactive Safety (INV-1 / INV-2):** Provide early warning advisories without interfering with or altering existing hard/soft fail-safe thresholds.
- **Zero Performance & Memory Overhead:** Pure in-memory streaming computation (O(1) time and memory complexity per telemetry tick).
- **Non-Spammy User Experience:** Advisories must incorporate strict rate limiting and cooldown periods (minimum 5 minutes between toast notifications).

---

## 3. Considered Options

1. **Option A: Real-time graphical plot in GUI.**
   - *Rejected for v1.8.5:* Heavyweight UI overhaul requiring complex charting libraries; would increase memory footprint and GUI rendering overhead.
2. **Option B: Purely external log post-processor script.**
   - *Rejected:* Does not provide live visibility in the system tray or proactive in-session notifications to the user.
3. **Option C: In-memory `SessionMetricsTracker` with Tray peak display, proactive advisory toasts, and diagnostics export.**
   - *Accepted:* Lightweight, high-impact, thread-safe, and seamlessly integrates with `TelemetryWorker` and `Diagnostics`.

---

## 4. Architecture Design

### 4.1 Component: `SessionMetricsTracker` (`src/Backend/SessionMetricsTracker.py`)
Encapsulates all session-level statistics:
- `session_start_ts`: Unix timestamp of session initialization.
- `sample_count`: Total snapshots processed.
- `peak_cpu_temp`, `peak_gpu_temp`: Maximum temperatures observed.
- `min_cpu_temp`, `min_gpu_temp`: Minimum temperatures observed (post-startup).
- `sum_cpu_temp`, `sum_gpu_temp`: Cumulative sums for computing arithmetic averages.
- `peak_cpu_rpm`, `peak_gpu_rpm`: Maximum fan speeds observed.
- `high_temp_excursion_seconds`: Cumulative seconds spent with CPU >= 90°C or GPU >= 82°C.
- `failsafe_trip_count`: Total emergency fail-safe trips triggered during the session.

### 4.2 Proactive Thermal Advisory Toast
- Condition: If CPU temp >= 90°C or GPU temp >= 82°C persists for consecutive 30 seconds while active profile is `Quiet` or `Balanced`.
- Cooldown: Enforces a 300-second (5-minute) minimum delay between advisory notifications to eliminate notification fatigue.
- Safety: Advisory is purely informative; does not override user mode settings unless the hard/soft fail-safe triggers.

### 4.3 Tray Tooltip Enhancement
Expands tray tooltip to include peak values:
```text
GPU: 68 °C (Peak: 81 °C)    2400 RPM
CPU: 74 °C (Peak: 93 °C)    2700 RPM
Mode: Balanced (Trips: 0)
```

### 4.4 Diagnostics Bug Report Integration
`Diagnostics.build()` invokes `tracker.get_summary()` and writes `session_metrics.json` into the root of `bugreport-<stamp>.zip`.

---

## 5. Consequences & Invariants

- **INV-1 (Safety Priority):** Unaffected. Hard emergency trips (CPU >= 100°C) and soft fail-safe trips continue to operate independently.
- **INV-2 (Timeout Bounds):** O(1) arithmetic updates take < 0.05 ms per snapshot, well within the 1000ms latency ceiling.
- **Verification:** Unit tests covering tracking accuracy, None handling, excursion timing, rate-limited advisories, and diagnostics export.
