"""Env + logic self-check for the G15 5530 fork. Run: .venv\\Scripts\\python.exe tools\\check_env.py"""
import sys, os
SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, SRC)
sys.argv = ["tcc-g15.py"]

import PySide6
print("PySide6", PySide6.__version__)

for mod in ["GUI.AppGUI", "GUI.HotKey", "GUI.QGaugeTrayIcon", "GUI.QGauge", "GUI.QRadioButtonSet",
            "GUI.ThermalUnitWidget", "GUI.AppColors", "Backend.AWCCWmiWrapper", "Backend.AWCCThermal",
            "Backend.DetectHardware"]:
    __import__(mod)
print("imports: 10/10 ok")

from Backend.AWCCWmiWrapper import AWCCWmiWrapper as W
from Backend.AWCCThermal import clearStaleComCache
from GUI.AppGUI import TCC_GUI, MODE_ORDER


class FakeAwcc:
    """Accepts only the mode ids in `accepted`; everything else answers -1 like the real board."""

    def __init__(self, accepted=()):
        self.calls = []
        self.accepted = set(accepted)

    def Thermal_Information(self, arg):
        self.calls.append(("TI", arg)); return (0,)

    def GetFanSensors(self, arg):
        self.calls.append(("GF", arg)); return (0,)

    def Thermal_Control(self, arg):
        self.calls.append(("TC", arg))
        return (0,) if (arg >> 8) in self.accepted else (-1,)


def last_mode(fake):
    return [a for m, a in fake.calls if m == "TC"][-1] >> 8


# --- bit packing -------------------------------------------------------------
f = FakeAwcc({0xA0, 0xAB}); w = W(f)
w.GetSensorTemperature(1); w.GetFanRPM(0x31); w.SetAddonSpeedPercent(0x31, 100)
assert f.calls[:3] == [("TI", (1 << 8) | 4), ("TI", (0x31 << 8) | 5), ("TC", (100 << 16) | (0x31 << 8) | 2)], f.calls
print("bit packing: ok")

# --- 5530 firmware: only the USTT ids answer 0 (measured with tools/mode_probe.py)
f = FakeAwcc({0xA0, 0xA1, 0xA3, 0xAB, 0x97}); w = W(f)
assert w.ApplyThermalMode(W.ThermalMode.Balanced) and last_mode(f) == 0xA0, hex(last_mode(f))
assert w.ApplyThermalMode(W.ThermalMode.Quiet) and last_mode(f) == 0xA3
assert w.ApplyThermalMode(W.ThermalMode.Performance) and last_mode(f) == 0xA1
assert w.ApplyThermalMode(W.ThermalMode.G_Mode) and last_mode(f) == 0xAB
assert 0 not in [last_mode(f)], "must never silently send Custom"
print("ustt firmware (5530): ok — balanced 0xA0, quiet 0xA3, performance 0xA1")

# --- legacy firmware: plain ids only (150/152/153 family)
f = FakeAwcc({0x96, 0x97, 0x98, 0xAB}); w = W(f)
assert w.ApplyThermalMode(W.ThermalMode.Balanced) and last_mode(f) == 0x97
assert w.ApplyThermalMode(W.ThermalMode.Quiet) and last_mode(f) == 0x96
assert w.ApplyThermalMode(W.ThermalMode.Performance) and last_mode(f) == 0x98
print("legacy firmware: ok — falls back to plain ids")

# --- unsupported mode is refused, not faked
f = FakeAwcc({0x97}); w = W(f)
assert w.ApplyThermalMode(W.ThermalMode.Quiet) is False
print("unsupported mode: refused")

# --- Custom(0) must survive the falsy check
f = FakeAwcc({0}); w = W(f)
assert w.ApplyThermalMode(W.ThermalMode.Custom) is True and last_mode(f) == 0
print("custom mode 0: ok")

# --- resolved mode is cached: a second apply does not re-probe
f = FakeAwcc({0xA3}); w = W(f)
w.ApplyThermalMode(W.ThermalMode.Quiet)
n = len([c for c in f.calls if c[0] == "TC"])
w.ApplyThermalMode(W.ThermalMode.Quiet)
assert len([c for c in f.calls if c[0] == "TC"]) == n + 1, "should reuse the cached id"
print("mode cache: ok")

# --- invalid WMI answers -----------------------------------------------------
class Negative(FakeAwcc):
    def Thermal_Information(self, arg): return (-2,)
class Huge(FakeAwcc):
    def Thermal_Information(self, arg): return (0xFFFFFFFF,)
assert W(Negative()).GetFanRPMPercent(0x32) is None, "-2 must be treated as no data"
assert W(Huge()).GetSensorTemperature(1) is None, "0xFFFFFFFF must be treated as no data"
print("invalid WMI values: ok")

# --- temperature plausibility ------------------------------------------------
assert TCC_GUI._saneTemp(2) is None
assert TCC_GUI._saneTemp(66) == 66
assert TCC_GUI._saneTemp(None) is None
assert TCC_GUI._saneTemp(200) is None
print("temperature guard: ok")

# --- UI order exposes the new profiles ---------------------------------------
names = [m.name for m in MODE_ORDER]
assert names == ["Auto", "Balanced", "G_Mode", "Custom"], names
print("mode switch order: ok", names)

# --- COM cache helper is safe to call when there's nothing to clean ----------
assert isinstance(clearStaleComCache(), bool)
print("com cache helper: ok")

# --- model whitelist ---------------------------------------------------------
from Backend.DetectHardware import DetectHardware
from GUI.AppGUI import watchdogCommand, HEARTBEAT_FILE

assert DetectHardware.isSupportedModel('Dell Inc. Dell G15 5530')
assert DetectHardware.isSupportedModel('Dell Inc. Dell G15 5520')
assert not DetectHardware.isSupportedModel('Dell Inc. XPS 13 9310')
assert not DetectHardware.isSupportedModel(None)
os.environ.pop('TCC_ALLOW_UNSUPPORTED', None)
assert DetectHardware.isUnsupportedAllowed() is False
os.environ['TCC_ALLOW_UNSUPPORTED'] = '1'
assert DetectHardware.isUnsupportedAllowed() is True
os.environ.pop('TCC_ALLOW_UNSUPPORTED', None)
print('model whitelist: ok')

# --- watchdog is wired up ----------------------------------------------------
cmd = watchdogCommand(HEARTBEAT_FILE)
assert cmd and cmd[-1] == HEARTBEAT_FILE, cmd
assert os.path.exists(cmd[1] if len(cmd) > 2 else cmd[0]), 'watchdog script missing'
print('watchdog command: ok')

# --- diagnostics module imports and builds a url ------------------------------
from GUI import Diagnostics
url_ok = Diagnostics.REPO == 'morshedmilton/tcc-g15'
assert url_ok
print('diagnostics module: ok')

print("ALL CHECKS PASSED")
