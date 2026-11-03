"""Hardware test: which thermal modes does this 5530 firmware actually accept?
Elevated. Applies each candidate mode, samples fan/temp response, restores Balanced.
Auto-aborts if CPU sensor >= 95 C or GPU (NVML) >= 88 C.
Writes docs/baseline/mode_probe.json
"""
import json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "docs" / "baseline" / "mode_probe.json"

CANDIDATES = [
    ("Quiet", 150),
    ("Performance", 152),
    ("FullSpeed", 153),
    ("USTT_Quiet", 163),
    ("USTT_Performance", 161),
    ("USTT_Cool", 162),
    ("USTT_FullSpeed", 164),
    ("G_Mode", 171),
]
SETTLE_SEC = 18
SAMPLE_SEC = 6


def main() -> int:
    from Backend.AWCCThermal import AWCCThermal
    from Backend.AWCCWmiWrapper import AWCCWmiWrapper as W

    awcc = AWCCThermal()
    w = awcc._awcc
    nvml_temp = None
    try:
        import pynvml as n
        n.nvmlInit()
        h = n.nvmlDeviceGetHandleByIndex(0)
        def nvml_temp():
            return n.nvmlDeviceGetTemperature(h, n.NVML_TEMPERATURE_GPU)
    except Exception:
        pass

    def snapshot():
        temps = awcc.getAllTemp()
        rpm = awcc.getAllFanRPM()
        gpu = nvml_temp() if nvml_temp else None
        return {"temps": temps, "rpm": rpm, "nvml_gpu_c": gpu}

    results = {"model": "Dell G15 5530", "bios": "1.36.0", "candidates": [], "baseline_before": snapshot()}
    print("baseline:", results["baseline_before"], flush=True)

    def unsafe(s):
        cpu = [t for t in s["temps"] if t is not None]
        if any(t >= 95 for t in cpu):
            return f"CPU >= 95C ({cpu})"
        if s.get("nvml_gpu_c") is not None and s["nvml_gpu_c"] >= 88:
            return f"GPU >= 88C ({s['nvml_gpu_c']})"
        return None

    for name, value in CANDIDATES:
        entry = {"name": name, "mode_value": value}
        # SetAddonSpeedPercent/direct _Thermal_Control bypasses the balanced patch logic
        try:
            t0 = time.perf_counter()
            rc = w._call("Thermal_Control", (value << 8) | 1)
            entry["apply_ms"] = round((time.perf_counter() - t0) * 1000)
            entry["return"] = rc              # 0 = accepted, None = call failed
            entry["accepted"] = (rc == 0)
        except Exception as ex:
            entry["return"] = None
            entry["accepted"] = False
            entry["error"] = f"{type(ex).__name__}: {ex}"

        print(f"{name:16} value={value:3} return={entry.get('return')} accepted={entry.get('accepted')}", flush=True)
        time.sleep(SETTLE_SEC)

        samples = []
        for _ in range(3):
            s = snapshot()
            samples.append(s)
            reason = unsafe(s)
            if reason:
                entry["aborted"] = reason
                print(f"  ABORT: {reason}", flush=True)
                break
            time.sleep(SAMPLE_SEC)
        entry["samples"] = samples
        results["candidates"].append(entry)
        if entry.get("aborted"):
            break

    # always restore
    restore_ok = awcc.setMode(W.ThermalMode.Balanced)
    results["restore_balanced"] = {"ok": restore_ok, "after": snapshot()}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("restored Balanced:", restore_ok, flush=True)
    print(f"written: {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())