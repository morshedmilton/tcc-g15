"""Run the diagnostics bundle once and print what it produced."""
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from GUI import Diagnostics

zipPath, url = Diagnostics.build("Thermal Control Center for Dell G15", "1.8.0-dev")
print("zip:", zipPath, "exists:", os.path.exists(zipPath) if zipPath else False)
if zipPath:
    print("size:", os.path.getsize(zipPath), "bytes")
    import zipfile
    with zipfile.ZipFile(zipPath) as z:
        print("entries:", z.namelist())
        print("system.json:", z.read("system.json").decode()[:200])
        print("awcc.json:", z.read("awcc.json").decode()[:300])
print("url:", url[:160])
