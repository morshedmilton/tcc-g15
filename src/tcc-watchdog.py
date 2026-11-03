# (c) github.com/AlexIII, fork by github.com/morshedmilton
# GPLv3
"""Watchdog: if the GUI dies without cleaning up, put the firmware back into Balanced.

The GUI touches a heartbeat file once per poll. When the heartbeat goes stale (crash,
kill -9, a hang) this process sets Balanced and exits. Started and stopped by the GUI;
runs with the same elevation, no UI, ~4 MB.
"""
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HEARTBEAT_TIMEOUT_SEC = 12.0
POLL_SEC = 2.0


def main() -> int:
    if len(sys.argv) < 2:
        print('usage: tcc-watchdog.py <heartbeat-file>', file=sys.stderr)
        return 2

    heartbeat = Path(sys.argv[1])

    from Backend.AWCCThermal import AWCCThermal, NoAWCCWMIClass, CannotInstAWCCWMI
    from Backend.AWCCWmiWrapper import AWCCWmiWrapper

    try:
        awcc = AWCCThermal()
    except (NoAWCCWMIClass, CannotInstAWCCWMI) as ex:
        print(f'watchdog: cannot reach the thermal interface ({type(ex).__name__})', file=sys.stderr)
        return 1

    print(f'watchdog: watching {heartbeat}', flush=True)

    suspend_grace_until = 0.0
    while True:
        t0 = time.monotonic()
        time.sleep(POLL_SEC)
        elapsed = time.monotonic() - t0

        now_mono = time.monotonic()
        # If sleep took significantly longer than POLL_SEC, system suspended (sleep/hibernate/modern standby)
        if elapsed > (POLL_SEC + 4.0):
            print(f'watchdog: system resume detected (sleep elapsed {elapsed:.1f}s), granting {HEARTBEAT_TIMEOUT_SEC}s grace', flush=True)
            suspend_grace_until = now_mono + HEARTBEAT_TIMEOUT_SEC
            continue

        if now_mono < suspend_grace_until:
            continue

        try:
            age = time.time() - heartbeat.stat().st_mtime
        except FileNotFoundError:
            age = HEARTBEAT_TIMEOUT_SEC + 1

        if age > HEARTBEAT_TIMEOUT_SEC:
            ok = awcc.setMode(AWCCWmiWrapper.ThermalMode.Balanced)
            # marker so a test (or the user) can see that the watchdog fired
            try:
                heartbeat.with_name(heartbeat.name + '.restored').write_text(
                    f'{datetime.now().isoformat()} ok={ok} age={age:.0f}s', encoding='utf-8')
            except OSError:
                pass
            print(f'watchdog: heartbeat stale ({age:.0f}s), restored Balanced: {ok}', flush=True)
            return 0


if __name__ == '__main__':
    sys.exit(main())
