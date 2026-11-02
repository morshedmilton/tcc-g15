"""Emergency rollback: puts the thermal interface back into Balanced mode.
Elevated. Prints the firmware answer. Safe to run at any time.

    python tools/restore_default_mode.py           # Balanced (0x97, USTT probe if needed)
    python tools/restore_default_mode.py --probe   # read-only: dump temps + fans, change nothing
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    from Backend.AWCCThermal import AWCCThermal
    from Backend.AWCCWmiWrapper import AWCCWmiWrapper

    probe_only = "--probe" in sys.argv
    awcc = AWCCThermal()

    if probe_only:
        print("mode: (unknown — firmware has no getter)")
        print("fans:", awcc._fanIdsAndRelatedSensorsIds)
        print("temps:", awcc.getAllTemp())
        print("rpm:", awcc.getAllFanRPM())
        return 0

    ok = awcc.setMode(AWCCWmiWrapper.ThermalMode.Balanced)
    print(f"set Balanced: {'ok' if ok else 'FAILED'}")
    print("temps after:", awcc.getAllTemp())
    print("rpm after:", awcc.getAllFanRPM())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())