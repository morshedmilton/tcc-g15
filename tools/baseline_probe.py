"""Baseline probe: samples the running tcc-g15 process + hardware telemetry.
Elevated. Writes CSV incrementally so progress survives a crash.

Usage: python tools/baseline_probe.py <target_pid> <idle_sec> <cpu_sec>
"""
import csv, json, math, os, subprocess, sys, threading, time
from datetime import datetime
from pathlib import Path

# burn mode: one process per core, no GIL ceiling
if len(sys.argv) > 1 and sys.argv[1] == '--burn':
    x = 1.0
    while True:
        for _ in range(20000):
            x = math.sin(x) * math.cos(x) + 0.1

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "baseline"
OUT.mkdir(parents=True, exist_ok=True)
TS = datetime.now().strftime("%Y%m%d-%H%M%S")
CSV = OUT / f"baseline-{TS}.csv"
META = OUT / f"baseline-{TS}.json"
STRESS_PROCS = 10

sys.path.insert(0, str(ROOT / "src"))
import psutil

# ---------- hardware readers ----------
_nvml = None
def gpu_reader():
    global _nvml
    try:
        import pynvml as n
        n.nvmlInit()
        h = n.nvmlDeviceGetHandleByIndex(0)
        def read():
            try:
                return {
                    "gpu_temp_c": n.nvmlDeviceGetTemperature(h, n.NVML_TEMPERATURE_GPU),
                    "gpu_power_w": round(n.nvmlDeviceGetPowerUsage(h) / 1000.0, 1),
                }
            except Exception:
                return {}
        _nvml = n
        return read
    except Exception:
        return lambda: {}

def awcc_reader():
    """Fan RPM / CPU-GPU temps through the Dell WMI interface (needs admin)."""
    try:
        from Backend.AWCCWmiWrapper import AWCCWmiWrapper
        from wmi import WMI
        inst = WMI(namespace="root\\WMI").AWCCWmiMethodFunction()[0]
        w = AWCCWmiWrapper(inst)
        fans = w.GetFanIdsAndRelatedSensorsIds()
        def read():
            try:
                out = {}
                for i, (fan_id, sensors) in enumerate(fans):
                    out[f"fan{i}_rpm"] = w.GetFanRPM(fan_id)
                    out[f"fan{i}_temp_c"] = w.GetSensorTemperature(sensors[0]) if sensors else None
                return out
            except Exception:
                return {}
        return read, [(f, list(s)) for f, s in fans]
    except Exception as ex:
        return (lambda: {}), f"awcc unavailable: {type(ex).__name__}"

# ---------- cpu stress ----------
_stop = threading.Event()
def burn():
    x = 1.0
    while not _stop.is_set():
        for _ in range(5000):
            x = math.sin(x) * math.cos(x) + 0.1
            if _stop.is_set():
                return

def start_stress(n):
    procs = [subprocess.Popen([sys.executable, __file__, '--burn'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
             for _ in range(n)]
    return procs

def stop_stress(procs):
    for p in procs:
        try: p.kill()
        except Exception: pass
    for p in procs:
        try: p.wait(timeout=5)
        except Exception: pass

# ---------- main ----------
def main():
    pid = int(sys.argv[1])
    idle_sec = int(sys.argv[2]) if len(sys.argv) > 2 else 180
    cpu_sec = int(sys.argv[3]) if len(sys.argv) > 3 else 240

    proc = psutil.Process(pid)
    gpu = gpu_reader()
    hw, fan_map = awcc_reader()
    proc.cpu_percent()  # prime

    f = open(CSV, "w", newline="", encoding="utf-8")
    fields = ["ts", "phase", "cpu_pct", "ram_mb", "threads", "ctx_sw_total",
              "gpu_temp_c", "gpu_power_w", "fan0_rpm", "fan0_temp_c", "fan1_rpm", "fan1_temp_c"]
    wr = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    wr.writeheader(); f.flush()

    started = time.time()
    rows = 0
    def sample(phase):
        nonlocal rows
        try:
            row = {
                "ts": round(time.time() - started, 1),
                "phase": phase,
                "cpu_pct": round(proc.cpu_percent(), 2),
                "ram_mb": round(proc.memory_info().rss / 1024**2, 1),
                "threads": proc.num_threads(),
            }
            cs = proc.num_ctx_switches()
            row["ctx_sw_total"] = cs.voluntary + cs.involuntary
            row.update(gpu()); row.update(hw())
            wr.writerow(row); f.flush(); rows += 1
        except Exception:
            pass

    print(f"target pid {pid} | fan map {fan_map} | csv {CSV}", flush=True)
    print(f"phase idle {idle_sec}s", flush=True)
    t0 = time.time()
    while time.time() - t0 < idle_sec:
        sample("idle"); time.sleep(1)

    print(f"phase cpu {cpu_sec}s ({STRESS_PROCS} processes)", flush=True)
    ts = start_stress(STRESS_PROCS)
    t0 = time.time()
    while time.time() - t0 < cpu_sec:
        sample("cpu"); time.sleep(1)
    stop_stress(ts)

    print("phase cooldown 60s", flush=True)
    t0 = time.time()
    while time.time() - t0 < 60:
        sample("cooldown"); time.sleep(1)

    f.close()
    if _nvml:
        try: _nvml.nvmlShutdown()
        except Exception: pass

    META.write_text(json.dumps({
        "target_pid": pid, "csv": CSV.name, "rows": rows,
        "idle_sec": idle_sec, "cpu_sec": cpu_sec, "fan_map": str(fan_map),
        "model": "Dell G15 5530", "app": "installed tcc-g15 1.6.4 build (2025-01-15)",
    }, indent=2), encoding="utf-8")
    print(f"done: {rows} rows -> {CSV}", flush=True)

if __name__ == "__main__":
    main()