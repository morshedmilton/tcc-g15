# CYCLE-007 — Process-aware thermal profile switching: correctness & state-restoration audit

- **Scope**: `src/Backend/ProcessRule.py`, `src/Backend/ProcessRulePresets.py`, `src/GUI/ProcessMonitorWorker.py`, `src/GUI/ProcessRulesDialog.py`, and the mode-arbitration / fail-safe interaction in `src/GUI/AppGUI.py`.
- **Version under audit**: 1.8.6 (`AppGUI.py:295`, `APP_VERSION`), branch `main`.
- **Method**: static trace of every path that writes `_userOverride`, `_baselineMode`, `_missingCycles`, `_failsafeTrippedPrevModeStr`, `_modeSwitch` and the `process_rules` / `auto_switch_enabled` settings keys. No code was modified; no runtime execution was performed by this audit, so all findings are tiered accordingly.
- **Note on `applyMode`**: no symbol named `applyMode` exists in the tree (`grep applyMode src/` → 0 hits). The equivalent write path is the local closure `onModeChange()` at `AppGUI.py:639-678`, reached synchronously from `QRadioButtonSet.setChecked()` → `_onClicked()` (`QRadioButtonSet.py:90-93`, `109-112`). All mode-arbitration findings below refer to that closure.
- **Snapshot caveat (important)**: the working tree changed *during* this audit. An in-flight feature (`ThermalMode.Auto`, the `_fanCurveDriver`, `MODE_ORDER = [Auto, Balanced, G_Mode, Custom]` at `AppGUI.py:154`, legacy target coercion in `ProcessRule.py:30-31`) appeared between two reads of the same file (~30 lines inserted in `AppGUI.py`, ~22 in `ProcessRule.py`). Every line number below was re-verified against the post-change snapshot with the anchors quoted in the text. If lines drift again, match on the quoted snippet, not the number. Findings marked *pre-existing* are independent of the Auto work; findings marked *interacts with Auto* depend on the new coercion.

Severity scale used: **P0** safety invariant broken or data destroyed without a reachable recovery; **P1** user-visible loss of a documented guarantee or a crash-like failure with a realistic trigger; **P2** wrong behaviour in a narrower but reachable scenario; **P3** cosmetic/robustness.

## 1. Verdict

- **P0: none.** The two independent INV-1 barriers are real and hold in the normal path (see §4.1/§4.2): the scan slot returns before any rule logic while a trip is latched (`AppGUI.py:1180`), and `onModeChange` refuses to record a user override while a trip is latched (`AppGUI.py:641-646`). G_Mode (rank 5) also dominates every reachable rule target in arbitration (`ProcessRule.py:17-25`, `AppGUI.py:1217-1218`). I found no path by which a process rule can *initiate* a mode below G_Mode during an active trip.
- **P1: 2** — a manual selection made in the fail-safe window is discarded and then fought by the rule (DEF-701), and an *automatic* switch failure takes the fatal user-command path, killing the app and its watchdog without restoring Balanced (DEF-702).
- **P2: 8, P3: 5.**
- The specific hunt areas that came back **clean** are listed in §5 so the negatives are auditable.

## 2. Findings index

| ID | Sev | Area | One-line |
|---|---|---|---|
| DEF-701 | P1 | state machine | Manual mode choice during a latched fail-safe is not recorded as override, cancels the latch, and is reverted by the rule ≤2.5 s later (endless fight) |
| DEF-702 | P1 | fail-safe / exception | A rule-triggered `setMode` failure calls `_errorExit` → `_destroy` → watchdog stopped, no Balanced restore, `sys.exit` inside a queued slot |
| DEF-703 | P2 | state machine | `_userOverride` + stale `_baselineMode` survive automation off→on; automation is silently inert for the rest of the session |
| DEF-704 | P2 | precedence | The coerced `Auto` profile ranks **0**, i.e. below Balanced (2) and Custom (3) — precedence inversion vs the documented Performance slot |
| DEF-705 | P2 | fail-safe | Any non-G_Mode change clears the trip latch, including AC/battery automation and rules → post-trip hold can be abandoned, restore target replaced |
| DEF-706 | P2 | exception path | Latch is set before the write and cleared after it; an exception leaves process rules locked out and the UI/hardware divergent |
| DEF-707 | P2 | debounce/thread | Debounce counts *delivered scans*, not elapsed time; a GUI stall collapses the 4 s hysteresis (fan flapping) |
| DEF-708 | P2 | persistence | Corrupt/partial `process_rules` is replaced by 18 presets and then persisted over the user's data; `"enabled": "false"` parses as enabled |
| DEF-709 | P2 | persistence | The rule-applied mode is written to `app/mode` as the user's default; the baseline is never persisted |
| DEF-710 | P2 | state machine | The G-Key toggles *off* a rule-applied G_Mode and sets the override, killing automation for the session |
| DEF-711 | P3 | UI/config | The rule dialog offers `Performance`/`Quiet`, which are silently rewritten to `Auto`/`Balanced`; `Auto` cannot be chosen |
| DEF-712 | P3 | matching | Runtime alias matching is one-directional; `ProcessRule.matches()` is dead code |
| DEF-713 | P3 | config | An empty `target_mode` escapes coercion → no-op switch + a "Thermal mode changed" toast every 2.5 s |
| DEF-714 | P3 | Qt teardown | `stop()` cannot stop its timer from the GUI thread; worker/QTimer never deleted; `setInterval` is an unguarded cross-thread API |
| DEF-715 | P3 | debounce | `_missingCycles` is frozen while automation is disabled → a dead rule is applied for ~5 s after re-enable |

---

## 3. P1 findings

### DEF-701 — Manual selection in the fail-safe window is discarded, then fought by the rule
**Severity**: P1 · **Files**: `src/GUI/AppGUI.py:641-646`, `:674`, `:767-791`, `:1212-1213`, `:1220-1226`

**What the code does today.** `onModeChange` records a user override only when all three guards pass (`AppGUI.py:641-646`):

```python
if (not getattr(self, '_inAutoSwitch', False)
    and not getattr(self, '_inFailsafeSwitch', False)
    and getattr(self, '_failsafeTrippedPrevModeStr', None) is None):
    if getattr(self, '_baselineMode', None) is not None:
        self._userOverride = True
```

Immediately afterwards any non-G_Mode value clears the trip latch (`:673-674`): `if val != ThermalMode.G_Mode.value: self._failsafeTrippedPrevModeStr = None`. Note that the guard is *not* the "was this a user click?" test — it is "is a trip currently latched?" So a genuine user click in that window is the one case where the override is **not** recorded, while it is still allowed to change the mode and to destroy the latch.

**Concrete breaking scenario.** `cs2.exe` rule (preset) coerces to `Auto` (`ProcessRule.py:31`), baseline `Balanced`. CPU sits at 96 °C for 8 s → soft trip at `:766-775` → mode `G_Mode`, latch = `"Auto"`. Ten seconds later the CPU is at 92 °C and the user clicks **BALANCED** because the fans are loud:
1. `QRadioButtonSet.setChecked("Balanced")` checks the button and calls `onModeChange` synchronously (`QRadioButtonSet.py:90-93`, `109-112`).
2. `:643` sees the latch → `_userOverride` stays `False`; the firmware is switched to Balanced.
3. `:674` clears the latch, so the pending "restore to Auto after 60 s" at `:779-791` will never run.
4. The next scan (≤2.5 s) finds the rule still matching, `_baselineMode = "Balanced"` ≠ `None`, `_userOverride = False` → `:1212-1213` does not return → `:1220-1226` switches back to `Auto`.
5. The user clicks BALANCED again → steps 1-4 repeat. Each iteration is two firmware mode writes, two toasts and a fan ramp.

**User impact.** During and after a thermal event — exactly when the user is most likely to intervene — manual mode selection is unusable while any rule matches: the UI reverts every click within one poll. This contradicts the documented user-sovereignty guarantee (`docs/engineering/PRD.md:45-47`, `AC-0602.4`; `docs/engineering/ARCHITECTURE.md:244`) and produces a mode-oscillation loop (extra ACPI writes, fan hunting). The fail-safe restore target is also silently lost.

**Minimal remediation sketch.** Replace the three boolean/flag guards with an explicit origin argument (`onModeChange(val, source)` where source ∈ {user, rule, failsafe, power}), pass it from each call site (`:715`, `:771`, `:786`, `:1223`, `:1240`), and derive both decisions from it: only `source == "user"` may clear the latch, and `source == "user"` must always set `_userOverride` when `_baselineMode is not None` — regardless of the latch. Until that refactor exists, at minimum treat `_baselineMode is not None and _failsafeTrippedPrevModeStr is not None` as a user override and clear the latch in the same branch.

---

### DEF-702 — An automatic switch failure takes the fatal path, kills the watchdog and skips the Balanced restore
**Severity**: P1 · **Files**: `src/GUI/AppGUI.py:661-668`, `:900-905`, `:908-910`, `:924-942`

**What the code does today.** `onModeChange` has one failure policy for every origin (`:661-668`):

```python
res = self._awcc.setMode(modeEnum)
if not res:
    if val in (ThermalMode.Quiet.value, ThermalMode.Performance.value):
        ... disable the option, revert, return
    self._errorExit(f"Failed to set mode {val}", "Program terminated")
```

`Quiet`/`Performance` are no longer reachable (coerced away at `ProcessRule.py:57-59`, and absent from `MODE_ORDER` at `AppGUI.py:154`), so for every live target — `Auto` (→ firmware `Custom`, `:652-655`), `Balanced`, `Custom`, `G_Mode` — a single `False` return terminates the process. Unlike `onExit`, which writes Balanced first (`:900-902`), `_errorExit` goes straight to `_destroy()` (`:908-910`), which stops the watchdog (`:942`) and quits both worker threads, then calls `errorExit` → `sys.exit(1)`.

**Concrete breaking scenario.** `blender.exe` preset → `Performance` → coerced to `Auto`; the game/render app starts; `_onProcessesScanned` calls `setChecked("Auto")` → `onModeChange("Auto")` → `_awcc.setMode(self._awcc.Mode.Custom)` returns `False` once (AWCC service restarting, ACPI hiccup, a COM call that fails transiently, a machine where `Custom` is rejected). The app destroys its own threads, stops the watchdog, shows "Failed to set mode Auto — Program terminated", and exits with the firmware still in whatever profile was last applied. `sys.exit` is raised inside a queued Qt slot (`:1175`), which PySide6 reports rather than reliably unwinding, so the process can also linger with dead workers.

**User impact.** Launching a game or a render job can shut the controller down; because `_stopWatchdog()` runs before the exit, the detached recovery process that would normally return the machine to Balanced (`tcc-watchdog.py:17`, `:61`; INV-3) is gone. The user loses both the UI and the fail-safe path at the moment the machine is under load.

**Minimal remediation sketch.** Keep the fatal path only for explicit user commands. For `source != "user"` (rule/power/failsafe), treat `False` as retryable: log, toast once, keep `_lastGoodMode`, disable the offending rule for N minutes (or until the process set changes), and never call `_errorExit`; do not stop the watchdog on any path that exits without first writing Balanced.

---

## 4. P2 findings

### DEF-703 — Override and baseline survive automation off→on; automation goes silently inert
**Severity**: P2 · **Files**: `src/GUI/AppGUI.py:1176-1177`, `:1161-1172`, `:645-646`, `:1212-1213`

**Today.** With automation disabled the scan slot returns immediately (`:1176-1177`). The disable handler restores the baseline *only* when no override is active (`:1161-1163`): `if self._baselineMode is not None and not self._userOverride:`. Otherwise both `_baselineMode` and `_userOverride` are left as they were, and nothing clears them.

**Scenario.** Rule active (baseline `Balanced`, mode `Auto`) → user clicks `Custom` (override `True`) → the user opens Process Rules and unchecks the master toggle → `_loadProcessRules` skips the restore → the user re-checks it. Next scan: `_baselineMode` is still `Balanced` so no new baseline is captured (`:1207-1209`), and `_userOverride` is still `True`, so `:1212-1213` returns. Automation never fires again for the rest of that session; it recovers only when every matching process has exited for two cycles (`:1229-1232`) or after a restart. Nothing in the UI indicates that automation is inert — the master checkbox is checked.

**Impact.** "It just stopped switching" with no diagnosable cause; the user's only recovery is a restart. Contradicts `AC-0602.4`/`AC-0603.2`.

**Remediation.** Treat disabling automation (or replacing the rule set) as a session reset: `_baselineMode = None`, `_userOverride = False`, `_missingCycles.clear()` before returning; and gate the override capture at `:645-646` on `self._autoSwitchEnabled`.

### DEF-704 — The coerced `Auto` profile ranks 0, inverting the documented cooling order
**Severity**: P2 · **Files**: `src/Backend/ProcessRule.py:17-25`, `:30-31`, `:50-60`, `:76-78`; `src/GUI/AppGUI.py:1217-1218`

**Today.** Legacy and preset targets are rewritten at construction (`:57-59`): `Performance → Auto`, `Quiet → Balanced`, anything else → `Balanced`. But the severity map was not updated — it still contains `Performance: 4` and `Quiet: 1` and has **no `Auto` key** (`:17-25`), so `cooling_priority` returns `0` for every coerced rule (`:76-78`, `.get(..., 0)`). Reachable ranks are therefore `G_Mode 5 > Custom 3 > Balanced 2 > Auto 0`.

**Scenario.** `cs2.exe` → `Auto` (rank 0) and a user-added `teams.exe → Balanced` (rank 2) both match. `max(...)` at `:1217` picks Balanced and the firmware leaves the Adaptive/Custom profile for Balanced while the game runs. The same happens for any rule targeting `Custom` (rank 3) versus an `Auto` rule. With the shipped presets alone the inversion is invisible (only `Auto` and `G_Mode` are produced), which is why it is P2 rather than P1.

**Impact.** Silent selection of a weaker cooling profile in multi-rule arbitration; the documented matrix (`PRD.md:36-40`, `ADR-006 §5.2`) no longer describes the code. The stale `Performance`/`Quiet` keys also mask the gap from any test that only compares those two.

**Remediation.** Rank the *coerced* profile — add `"Auto": 4` to `COOLING_SEVERITY_ORDER` (keep 3/2/1 for Custom/Balanced/Quiet if legacy values must still be ordered) and add a test asserting that every entry of `VISIBLE_PROFILES` has a nonzero rank and that the order equals the documented one.

### DEF-705 — Any non-G_Mode change clears the trip latch, including AC/battery automation
**Severity**: P2 · **Files**: `src/GUI/AppGUI.py:673-674`, `:706-719`, `:766-775`, `:779-791`

**Today.** The latch is cleared by *any* successful non-G_Mode write (`:673-674`), not by a user action. The AC/battery automation writes modes under `_inAutoSwitch` (`:706-719`), so it passes the override guard but still clears the latch.

**Scenario.** Trip latched (mode `G_Mode`, latch `Auto`). The charger is unplugged → `:711-715` writes `Balanced` → `onModeChange` → `:674` clears the latch. In the same telemetry tick the fail-safe block re-evaluates: if the CPU has already fallen below 95 °C, `userTrip` is false (`:756-762`), so no re-trip occurs and `:779` sees `None` → no restore either. The machine stays in Balanced, the trip is over, and the `Auto` restore target is lost. If the temperature is still high the same tick re-trips, but the latch now records `Balanced`, so the eventual post-cooldown restore lands on the wrong profile. A rule-driven `Auto` write takes the same path.

**Impact.** The post-trip hold can be silently abandoned by an unrelated power event; the restore target changes; an extra firmware write lands during an emergency.

**Remediation.** Only a user-originated change may clear the latch (same `source` refactor as DEF-701); power/rule/failsafe writes must leave `_failsafeTrippedPrevModeStr` untouched.

### DEF-706 — The trip latch is not exception-safe; UI and firmware can diverge
**Severity**: P2 · **Files**: `src/GUI/AppGUI.py:767-776`, `:779-791`, `:661-670`; `src/GUI/QRadioButtonSet.py:90-93`, `:109-112`

**Today.** The latch is written *before* the mode write (`:767`) and cleared *after* the restore's try/finally (`:791`). `_lastGoodMode` is only updated after a successful write (`:670`), but the radio button has already changed state before `onModeChange` is entered (`QRadioButtonSet.py:91-93` checks the button, which emits `toggled` → `_onClicked` → callback).

**Scenario A (trip).** `setChecked(G_Mode)` → `setMode` raises (COM/ACPI error). The `finally` restores `_inAutoSwitch`/`_inFailsafeSwitch` (`:773-775`), the exception leaves the slot, and `_failsafeTrippedPrevModeStr` stays set while the mode never became G_Mode. Every subsequent tick re-evaluates `userTrip` (`:766`) and retries the failing write, and `_onProcessesScanned` stays locked out (`:1180`).
**Scenario B (restore).** The exception at the restore write skips `:791`; `_failsafeTempIsHighTs` is stale, so the 60 s condition at `:779` stays true and the restore is retried on every tick indefinitely.
**Scenario C (any failure).** `getChecked()` reports the new mode while the firmware kept the old one (`:670` never runs), so later comparisons (`:1220`) see "already applied" and never resynchronise.

**Impact.** Process rules can remain locked out after the emergency ended; the UI can display a mode the firmware never entered (the user then trusts a cooling profile that is not applied).

**Remediation.** Make the latch transactional: perform the write first, and set/clear the latch only in the success branch, with a bounded retry and a "desync" recovery that re-asserts the current `getChecked()` value against the firmware on the next tick.

### DEF-707 — The 4 s debounce counts delivered scans, not elapsed time
**Severity**: P2 · **Files**: `src/GUI/ProcessMonitorWorker.py:82-86`; `src/GUI/AppGUI.py:1184-1197`, `:1201-1203`

**Today.** The worker emits one payload per tick (`ProcessMonitorWorker.py:85-86`) and the GUI increments an integer counter per delivered payload (`:1184-1192`); a rule is "effective" while `_missingCycles < 2` (`:1195-1197`). No timestamps, no scan generation, no coalescing.

**Scenario.** The GUI thread is blocked for ~10 s — e.g. `_startWatchdog`'s `wmi.WMI()` (`AppGUI.py:992-995`) when the watchdog died, a modal message box, or a slow `setMode`. Four `processes_scanned` events queue up and are then delivered back-to-back in a few milliseconds (a queued connection preserves every emission). `_missingCycles` reaches 2 within milliseconds, so a single real 2.5 s absence is treated as ≥4 s and the mode reverts; when the game reappears the next scan re-applies it. That is exactly the fan flapping REQ-0603 exists to prevent.

**Impact.** Acoustic flapping and unnecessary mode writes under GUI load; the documented "≥4.0 s of continuous absence" (`PRD.md:56-63`) is not what the code measures.

**Remediation.** Store `last_seen_monotonic` per matched process and require `now - last_seen > 4.0` for exit; attach a monotonic scan id and drop stale payloads; or coalesce in the worker (skip an emit if the previous one has not been consumed).

### DEF-708 — Corrupt or partial rule config is replaced by presets and then persisted
**Severity**: P2 · **Files**: `src/GUI/ProcessRulesDialog.py:265-278`; `src/GUI/AppGUI.py:1146-1158`, `:1096`; `src/Backend/ProcessRule.py:128-133`

**Today.** Both loaders swallow every parse error and fall back to the presets (`ProcessRulesDialog.py:274-278`, `AppGUI.py:1153-1157`), with no distinction between "key absent" and "value corrupt" and no backup of the raw value. `_saveAppSettings` then writes the in-memory rule list back to `process_rules` whenever any of the seven tracked values changes (`AppGUI.py:1084-1096`; the rule list itself is not part of the dirty check). `from_dict` coerces types (`ProcessRule.py:132-133`).

**Scenario A (data loss + consent).** A truncated value (power loss during the registry/INI write, an interrupted shutdown, a hand edit) → `json.loads` raises → 18 presets, all `enabled`, five of them `G_Mode` → the next telemetry tick persists them → the user's custom rules are unrecoverable and automatic G_Mode switching is now armed without the user asking.
**Scenario B (silent semantic change).** `{"process_name": "x.exe", "enabled": "false"}` → `bool("false")` is `True` (`ProcessRule.py:133`) → a rule the user disabled runs. A dict missing `target_mode` becomes `Balanced` (`:132`), i.e. a downgrade of whatever the profile was meant to be.

**Impact.** Irreversible loss of configuration plus a silent change in thermal behaviour after a corruption event the user never sees.

**Remediation.** Separate "absent" from "corrupt"; on corrupt, preserve the raw string under a `process_rules_corrupt` key, set `auto_switch_enabled=False`, and surface a prompt instead of silently enabling presets. Parse `enabled` explicitly (`str(v).lower() in ("true","1")`) and validate `process_name`/`target_mode`, dropping or flagging invalid entries instead of defaulting them.

### DEF-709 — The rule-applied mode becomes the persisted default
**Severity**: P2 · **Files**: `src/GUI/AppGUI.py:1071-1096`, `:833`, `:1108-1112`, `:1207-1209`

**Today.** `_saveAppSettings` persists `self._modeSwitch.getChecked()` (`:1072`, `:1088`), and it is called at the end of every telemetry tick (`:833`). `_baselineMode` and `_userOverride` are not persisted at all.

**Scenario.** A game is running and the rule has applied `Auto`; the user quits the app while the game is still up (or the app crashes). The last tick wrote `app/mode = "Auto"`. On the next launch `_loadAppSettings` accepts it (`Auto` is in `MODE_ORDER`, `:1110-1112`) and the app starts in the rule's profile with no matching process — the user's `Balanced` idle default is gone. The same happens for a crash mid-session, where nothing restores the baseline.

**Impact.** A persistent, unexplained change of the startup profile (fan behaviour at every boot) that the user must notice and undo manually; the documented "restore the baseline" contract ends at process exit and does not survive a restart.

**Remediation.** Persist `self._baselineMode or current` as `app/mode` while a rule session is active (optionally also store `app/session_mode` for diagnostics), or mark the persisted value as rule-applied and ignore it on load when no matching process is present.

### DEF-710 — The G-Key toggles off a rule-applied G_Mode and suppresses the rule
**Severity**: P2 · **Files**: `src/GUI/AppGUI.py:1038-1045`, `:645-646`, `:1212-1213`

**Today.** The hotkey handler only asks "is the current mode G_Mode?" (`:1039-1041`); it does not know who set it. Every rule-driven G_Mode is therefore indistinguishable from a hotkey-driven one.

**Scenario.** `cyberpunk2077.exe` (preset → `G_Mode`) is applied by the rule. The user presses the G-Key expecting "engage G-Mode": `:1040` is true → `setChecked(self._gModeKeyPrevModeStr or "Balanced")` → the mode drops to Balanced; because `_baselineMode` is set, `:645-646` also sets `_userOverride = True`, which suppresses the rule for the rest of the session. Pressing the key again sets `_gModeKeyPrevModeStr = "Balanced"` and returns to G_Mode, with the override still latched.

**Impact.** The documented "G-Key engages G-Mode" (`PRD.md:45`) behaves inversely during any rule session and permanently disables automation for that session; the user experiences a single key press as "turn off cooling".

**Remediation.** Track the origin of G_Mode (`_gModeOwner ∈ {hotkey, rule, failsafe}`); only toggle back when the hotkey owns it; a hotkey press during a rule session should be treated as a user directive toward G_Mode and recorded as an override *without* clearing the rule.

---

## 5. P3 findings

### DEF-711 — The dialog offers profiles the engine rewrites
`ProcessRulesDialog.py:15` still lists `["Performance", "G_Mode", "Balanced", "Quiet", "Custom"]`, while `ProcessRule.VISIBLE_PROFILES` is `("Auto", "Balanced", "G_Mode", "Custom")` (`ProcessRule.py:30`) and construction coerces (`:57-59`, applied at `ProcessRulesDialog.py:181`). A user who picks "Performance" gets "Auto" written to the table; "Quiet" becomes "Balanced"; and `Auto` itself cannot be selected deliberately. **Impact**: the saved configuration differs from the choice the user made, with only a log line to explain it. **Fix**: populate the combo from `VISIBLE_PROFILES`, and display legacy values as `Performance (legacy → Auto)` if they must remain loadable.

### DEF-712 — Alias matching is one-directional in the live path; `matches()` is unused
`AppGUI.py:1187` implements only `r.process_name == "bg3.exe" and "bg3_dx11.exe" in active_names`, while `ProcessRule.matches()` (`ProcessRule.py:80-100`) implements both directions and is never called (grep: only the definition). A user rule for `bg3_dx11.exe` never fires when `bg3.exe` runs, although REQ-0604 documents the alias as symmetric. **Fix**: call `r.matches()` from the scan loop and the debounce bookkeeping, or delete the dead method.

### DEF-713 — Empty `target_mode` escapes coercion and produces a toast loop
`__post_init__` only coerces inside `if self.target_mode:` (`ProcessRule.py:52`), so `{"process_name": "x.exe", "target_mode": ""}` keeps `""`: rank 0 (`:78`), it wins `max` when alone (`AppGUI.py:1217`), `setChecked("")` finds no button and does nothing (`QRadioButtonSet.py:90-93`), `getChecked() != ""` stays true, so `:1220-1226` fires a no-op write plus a "Thermal mode changed" toast every 2.5 s while the process runs. **Fix**: coerce empty/whitespace targets to Balanced and drop rules with an empty process name at load.

### DEF-714 — Worker teardown leaves an active timer in a dead thread
`stop()` only stops the timer when called from the worker thread (`ProcessMonitorWorker.py:46`), but `_destroy` calls it directly from the GUI thread (`AppGUI.py:936`) and then quits the thread (`:938-939`). The timer therefore stays active; the worker is never `deleteLater`-ed, so the `QTimer` (child of the worker, `ProcessMonitorWorker.py:33`) is eventually destroyed from the interpreter/GC thread → `QObject::killTimer: Timers cannot be stopped from another thread` at exit, or a hang if `wait(1000)` times out. `setInterval` (`:53-57`) is an unguarded cross-thread API (no caller today, verified by grep). **Fix**: invoke `stop` via a queued connection, connect `thread.finished` → `worker.deleteLater()`, and route interval changes through a slot.

### DEF-715 — Presence counters freeze while automation is off
`_onProcessesScanned` returns before the counter update when automation is disabled (`AppGUI.py:1176-1177`, `:1184-1192`). Disable for 20 minutes while `cs2.exe` runs, then let the game exit, then re-enable: the counter is still `0`, so the dead rule is "effective" (`:1195-1197`) and applies `Auto`/`G_Mode` on the desktop for up to two cycles (~5 s) before pruning restores the baseline. **Fix**: clear `_missingCycles` on toggle, or treat a gap larger than ~2× the interval as unknown and re-seed from the first scan.

---

## 6. Verified clean (negative results, for auditability)

| # | Question | Result | Evidence |
|---|---|---|---|
| C1 | Is a Qt object or `_awcc` call touched from the monitor thread? | **No.** The timer is created in `start()` on the worker thread; `scan_once` only calls `psutil`; the only cross-thread output is `processes_scanned.emit`. | `ProcessMonitorWorker.py:29-40`, `:59-79`, `:82-86` |
| C2 | Can a rule downgrade the firmware while a trip is latched? | **No** in the normal path: the scan slot returns before any rule logic, and `onModeChange` refuses to record an override. (The latch-clearing holes are DEF-701/DEF-705, which act *after* the latch is gone.) | `AppGUI.py:1180`, `:641-646` |
| C3 | Does G_Mode dominate multi-rule arbitration? | **Yes** for every reachable target: 5 vs max 3 (`Custom`). | `ProcessRule.py:17-25`, `AppGUI.py:1217-1218` |
| C4 | Is the baseline overwritten by later launches? | **No.** It is captured only when `_baselineMode is None` and cleared only on session end. | `AppGUI.py:1207-1209`, `:1229-1236` |
| C5 | Two matching processes with the same target | Deterministic (first in list wins `max`); no flapping. | `AppGUI.py:1217` |
| C6 | Does process scanning run on the GUI thread (heartbeat starvation)? | **No.** Scanning is entirely in the worker thread; the heartbeat risk comes from the WMI writes a rule can trigger (DEF-702/DEF-707), not from scanning. | `AppGUI.py:861-866`, `:833` |

## 7. Suspicions (not confirmed — do not treat as findings)

1. **Slot affinity**: `_onProcessesScanned` is not decorated with `@Slot` (`AppGUI.py:1175`). I believe PySide6 uses the bound method's `self` (a QObject) as the receiver context, so the queued signal is delivered on the GUI thread; I could not execute a threaded test to prove it. If it were instead treated as a plain functor, every rule switch would run on the scanner thread — a severe cross-thread violation. Adding `@Slot(set)` removes the ambiguity at zero cost.
2. **Mutable payload**: `processes_scanned = QtCore.Signal(set)` (`ProcessMonitorWorker.py:20`) carries a mutable Python object by reference across the queued connection. Safe today because a fresh set is built per scan (`:85`), but any future reuse/mutation of that set would be a data race.
3. **Teardown**: the leaked `QTimer` in DEF-714 may or may not emit Qt warnings or crash at interpreter exit; unverified without a live run.
4. **Multiple instances**: `createAppLockFile` (`src/tcc-g15.py:26-38`) unlinks an existing lock and always succeeds, so two instances can run and race on `process_rules` (`AppGUI.py:1096`). Inferred from the code; not reproduced.
5. **Firmware acceptance of `Custom`** (used for `Auto`, `AppGUI.py:652-655`) on every whitelisted model — unverified. If it can fail, DEF-702's trigger probability rises.
6. **Scan cost** vs the `<25 ms` claim (`PRD.md` AC-0601.2) and INV-3's "GUI thread never starved" — not measured here.

## 8. Regression tests that should exist and do not

The existing suites exercise the happy paths (`tests/test_process_monitor.py:139-260`, `tests/test_opp008_adversarial_stress.py:100-212`, `:289-346`, `:354-401`) but none of the following. Suggested names/locations follow the current layout.

| # | Test (suggested) | Setup | Expected assertion | Guards |
|---|---|---|---|---|
| T1 | `test_manual_choice_during_failsafe_window_sticks` (`tests/test_opp008_adversarial_stress.py`) | Rule `cs2.exe → Performance`; apply; latch a trip (`_failsafeTrippedPrevModeStr="Auto"`, mode `G_Mode`); call `_modeSwitch.setChecked("Balanced")`; run 3 scans with `{"cs2.exe"}` | Mode stays `Balanced`; `_userOverride is True`; latch cleared | DEF-701 |
| T2 | `test_automatic_switch_failure_never_exits` | `mock_awcc.setMode.return_value = False`; drive `_onProcessesScanned({"blender.exe"})` | `_errorExit` is **not** called; watchdog still alive (patch `_stopWatchdog` and assert not called); firmware mode unchanged; one toast at most | DEF-702 |
| T3 | `test_master_toggle_off_on_resets_session` | Rule applied, then user override, then `auto_switch_enabled=False` → `_loadProcessRules()` → `True` → `_loadProcessRules()`; scan with the process present | `_userOverride is False`, `_baselineMode is None`, rule re-applies | DEF-703 / DEF-715 |
| T4 | `test_cooling_rank_covers_every_visible_profile` | Iterate `VISIBLE_PROFILES` and the documented order | `cooling_priority` strictly decreases in the documented order; `Auto` ranks above `Balanced`/`Custom` | DEF-704 |
| T5 | `test_failsafe_latch_survives_power_transition` | Latched trip at `G_Mode`; flip AC→battery; run one tick with cool temps | Latch unchanged; no Balanced write while latched; restore still targets the recorded mode | DEF-705 |
| T6 | `test_setmode_exception_leaves_no_permanent_lockout` | `mock_awcc.setMode.side_effect = RuntimeError` during trip, then cool temps | Latch cleared (or retried with backoff) after recovery; `_onProcessesScanned` is not locked out afterwards | DEF-706 |
| T7 | `test_debounce_is_time_based_not_delivery_based` | 5 consecutive `_onProcessesScanned(set())` calls with `time.monotonic` patched to advance 20 ms | Mode unchanged (4 s of real absence not reached) | DEF-707 |
| T8 | `test_corrupt_process_rules_preserved` | QSettings `process_rules = "[{\"process_name\": \"x.exe\", \"target_mo"`; construct `ProcessRulesDialog` | Raw value preserved under a backup key; automation not silently enabled; `_save_to_settings` does not overwrite with presets | DEF-708 |
| T9 | `test_rule_mode_not_persisted_as_default` | Rule applied (`Auto`); call `_saveAppSettings`; construct a new `TCC_GUI` with the same settings | `SettingsKey.Mode` is the baseline (`Balanced`), not `Auto` | DEF-709 |
| T10 | `test_gkey_while_rule_holds_gmode` | Rule `cyberpunk2077.exe → G_Mode` applied; call `_onGModeHotKeyPressed()` | Mode stays `G_Mode` (or is recorded as an explicit override toward G_Mode), rule not silently disabled | DEF-710 |

## 9. Out-of-scope observations

- `_fanCurveDriver` and the `Auto` profile (`AppGUI.py:143-154`, `:795-812`) are a separate subsystem; this audit only checked its interaction with rules and the fail-safe. Two notes: the curve is skipped while a trip is latched (correct for INV-1), and a rule targeting `Auto` now selects firmware `Custom` plus the curve (`:652-655`), so the rule's effective cooling depends on curve state that the rule engine neither reads nor validates.
- `docs/engineering/ARCHITECTURE.md:272` and `docs/engineering/AUDIT.md:16` describe the `_userOverride`/latch behaviour as verified; neither mentions the fail-safe-window override gap (DEF-701) nor the automatic-switch fatal path (DEF-702). Any closure of these findings should update those tables as well as the ADR-006 state diagram (§5.4), which has no "fail-safe" state at all.
