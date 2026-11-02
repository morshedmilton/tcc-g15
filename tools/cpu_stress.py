"""Simple CPU stress using pure Python (no external deps)."""
import threading, time, math, sys

_stop = threading.Event()

def worker():
    # Busy loop doing floating point work
    x = 1.0
    while not _stop.is_set():
        for i in range(10000):
            x = math.sin(x) * math.cos(x) + 0.1
            if _stop.is_set():
                break

def stress_cpu(num_threads: int, duration_sec: int):
    threads = [threading.Thread(target=worker, daemon=True) for _ in range(num_threads)]
    for t in threads: t.start()
    print(f"  CPU stress: {num_threads} threads for {duration_sec}s")
    time.sleep(duration_sec)
    _stop.set()
    for t in threads: t.join(timeout=2)
    print("  CPU stress done")

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    d = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    stress_cpu(n, d)