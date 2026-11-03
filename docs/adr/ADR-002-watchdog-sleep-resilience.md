# ADR-002: Watchdog Sleep Resilience & Process Auto-Resurrection

**Date:** 2026-11-04  
**Status:** Accepted  
**Deciders:** Architect B, Safety Engineer E, Systems G, Reviewer L  

---

## Context

The detached hardware watchdog (`tcc-watchdog.exe`) is a critical safety component designed to satisfy Invariant **INV-3**: if the main application hangs, crashes, or is terminated (`taskkill /F`), the watchdog detects a stale heartbeat (> 12.0s) and forces the laptop firmware back into **Balanced** mode (`0xA0`).

However, during normal laptop use, users close the lid or Windows enters Modern Standby (S0ix) or S3 sleep. During sleep, wall-clock time (`time.time()`) advances by the full duration of the suspend (e.g. 30 minutes, 2 hours).

When the laptop resumes from sleep:
1. The heartbeat file's `st_mtime` reflects pre-sleep time.
2. The watchdog process woke up and calculated `age = time.time() - heartbeat.mtime`, which evaluated to hundreds or thousands of seconds.
3. The watchdog falsely diagnosed an application crash, forced firmware into Balanced, and **terminated with exit code 0**.
4. The main GUI process continued running unaware that the watchdog had died.
5. Consequently, if the application crashed anytime after the first sleep/resume, the laptop had **zero watchdog protection**, leaving fans frozen.

---

## Decision

We implement a dual-layer resilience architecture:

### 1. Watchdog Suspend Detection via Monotonic Loop Timing
Inside `tcc-watchdog.py`:
- Use `time.monotonic()` to measure the actual elapsed execution time across the polling sleep interval (`time.sleep(POLL_SEC)`).
- If `time.monotonic() - loop_start > (POLL_SEC + 4.0)`:
  - The process was suspended by the operating system (lid close / modern standby / sleep).
  - The watchdog logs a `system resume detected` event and resets its internal heartbeat tracking window.
  - This grants the GUI process a full `HEARTBEAT_TIMEOUT_SEC` grace period to resume its polling loop and touch the heartbeat file.

### 2. GUI Watchdog Auto-Resurrection
Inside `src/GUI/AppGUI.py`:
- In `updateAppState()`, check `if getattr(self, '_watchdog', None) and self._watchdog.poll() is not None: self._startWatchdog()`.
- If the watchdog process ever exits (due to an unhandled exception, accidental termination, or anomalous OS kill), the main GUI automatically spawns a fresh detached watchdog process.

---

## Consequences

- **Safety:** Invariant INV-3 is fully preserved. The system remains guarded across unlimited sleep/resume cycles.
- **Robustness:** Eliminates false positive emergency trips upon waking from sleep.
- **Fail-Safe Invariant:** If the GUI actually crashes during sleep, the grace period expires shortly after resume and the watchdog executes its emergency restore.
