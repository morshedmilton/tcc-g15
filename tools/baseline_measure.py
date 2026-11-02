"""Baseline measurement harness for tcc-g15 on Dell G15 5530.
Run elevated. Outputs CSV + JSON summary to docs/baseline/."""
import csv, json, os, psutil, time, threading, subprocess, sys, math
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # tcc-g15/
OUT_DIR = ROOT / "docs" / "baseline"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TS = datetime.now().strftime("%Y%m%d-%H%M%S")
CSV_FILE = OUT_DIR / f"baseline-{TS}.csv"
JSON_FILE = OUT_DIR / f"baseline-{TS}.json"

# ---- Pure-Python CPU stress -------------------------------------------------
_stress_stop = threading.Event()
def _stress_worker():
    x = 1.0
    while not _stress_stop.is_set():
        for i in range(10000):
            x = math.sin(x) * math.cos(x) + 0.1
            if _stress_stop.is_set(): break

def stress_cpu(num_threads: int, duration_sec: int):
    global _stress_stop
    _stress_stop = threading.Event()
    threads = [threading.Thread(target=_stress_worker, daemon=True) for _ in range(num_threads)]
    for t in threads: t.start()
    print(f"  CPU stress: {num_threads} threads for {duration_sec}s")
    time.sleep(duration_sec)
    _stress_stop.set()
    for t in threads: t.join(timeout=2)
    print("  CPU stress done")

# ---- Metrics collection -----------------------------------------------------
class MetricsCollector:
    def __init__(self, pid: int, interval_sec: float = 1.0):
        self.pid = pid
        self.interval = interval_sec
        self._stop = threading.Event()
        self.rows = []
        self.proc = psutil.Process(pid)

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=5)

    def _run(self):
        self.proc.cpu_percent()  # warm-up
        time.sleep(self.interval)
        while not self._stop.is_set():
            try:
                cpu = self.proc.cpu_percent()
                mem = self.proc.memory_info().rss / 1024 / 1024  # MB
                threads = self.proc.num_threads()
                ctx = self.proc.num_ctx_switches()
                wakeups = ctx.voluntary + ctx.involuntary
                now = datetime.now().isoformat()
                self.rows.append({
                    "timestamp": now,
                    "cpu_percent": round(cpu, 2),
                    "ram_mb": round(mem, 1),
                    "threads": threads,
                    "ctx_switches_total": wakeups,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            time.sleep(self.interval)

    def get_rows(self):
        return self.rows

# ---- Workload definitions ---------------------------------------------------
WORKLOADS = [
    ("idle", 300, None),                              # 5 min idle
    ("cpu_sustained", 600, lambda: stress_cpu(8, 600)),  # 10 min CPU
    # GPU load skipped (no FurMark) — will note in results
    ("mixed", 600, lambda: stress_cpu(4, 600)),       # 10 min mixed (lighter CPU)
]

# ---- Main -------------------------------------------------------------------
def main():
    print(f"=== tcc-g15 Baseline Measurement ===")
    print(f"Output dir: {OUT_DIR}")
    print(f"CSV: {CSV_FILE}")
    print(f"JSON: {JSON_FILE}")

    exe = ROOT / "src" / "tcc-g15.py"
    if not exe.exists():
        print("ERROR: src/tcc-g15.py not found")
        return 1

    print("Launching app elevated...")
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    proc = subprocess.Popen(
        [sys.executable, str(exe)],
        cwd=str(ROOT / "src"),
        startupinfo=startupinfo,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    print(f"App PID: {proc.pid}")

    print("Waiting for app to initialize WMI...")
    time.sleep(8)

    collector = MetricsCollector(proc.pid, interval_sec=1.0)
    collector.start()

    all_data = {
        "machine": "Dell G15 5530",
        "cpu": "i7-13650HX",
        "bios": "1.36.0",
        "app_version": "1.7.0",
        "workloads": [],
    }

    try:
        for name, duration, workload_fn in WORKLOADS:
            print(f"\n--- Workload: {name} ({duration}s) ---")
            workload_start = time.time()

            if workload_fn:
                # Run workload in background thread
                wl_thread = threading.Thread(target=workload_fn, daemon=True)
                wl_thread.start()
            else:
                wl_thread = None

            # Collect for duration
            while time.time() - workload_start < duration:
                time.sleep(15)
                elapsed = int(time.time() - workload_start)
                print(f"  {elapsed}/{duration}s...")

            if wl_thread:
                wl_thread.join(timeout=10)

            all_data["workloads"].append({
                "name": name,
                "planned_duration_sec": duration,
                "actual_duration_sec": round(time.time() - workload_start, 1),
            })

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        print("\nStopping app...")
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        collector.stop()

        # Save CSV
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            if collector.rows:
                writer = csv.DictWriter(f, fieldnames=collector.rows[0].keys())
                writer.writeheader()
                writer.writerows(collector.rows)
            print(f"Saved {len(collector.rows)} metric rows to {CSV_FILE}")

        # Save JSON summary
        all_data["total_metric_rows"] = len(collector.rows)
        all_data["collection_interval_sec"] = 1.0
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(all_data, f, indent=2)
        print(f"Saved summary to {JSON_FILE}")

    return 0

if __name__ == "__main__":
    sys.exit(main())