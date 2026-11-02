"""Measure cold/warm startup of the installed tcc-g15 (elevated).
Writes docs/baseline/startup.json. Restarts the app at the end."""
import json, subprocess, sys, time
from pathlib import Path
import psutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "baseline" / "startup.json"
EXE = r"C:\Program Files (x86)\Thermal Control Center\tcc-g15.exe"


def find_app():
    for p in psutil.process_iter(["name", "pid", "create_time"]):
        try:
            if p.info["name"] and p.info["name"].lower().startswith("tcc-g15"):
                return p
        except Exception:
            pass
    return None


def wait_window(timeout=40.0):
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < timeout:
        p = find_app()
        if p:
            try:
                # window is up when main window handle is non-zero
                import ctypes
                hwnd = ctypes.windll.user32.FindWindowW(None, "Thermal Control Center for Dell G15")
                if hwnd:
                    return (time.perf_counter() - t0) * 1000, p.pid
            except Exception:
                pass
        time.sleep(0.05)
    return None, None


def main():
    results = {}
    for attempt in ("cold", "warm"):
        old = find_app()
        if old:
            try:
                old.kill()
                old.wait(timeout=10)
            except Exception as e:
                results[attempt] = {"error": f"kill failed: {e}"}
                continue
            time.sleep(3)

        t0 = time.perf_counter()
        subprocess.Popen([EXE], close_fds=True)
        ms, pid = wait_window()
        if ms is None:
            results[attempt] = {"error": "window not detected in 40s"}
        else:
            results[attempt] = {"ms": round(ms), "pid": pid, "total_ms": round((time.perf_counter() - t0) * 1000)}
        time.sleep(2)

    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    sys.exit(main())