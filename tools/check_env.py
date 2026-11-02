"""Env + logic self-check for the G15 5530 fork. Run: .venv\\Scripts\\python.exe tools\\check_env.py"""
import sys, os
SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, SRC)
sys.argv = ["tcc-g15.py"]

import PySide6
from PySide6 import QtCore, QtWidgets
print("PySide6", PySide6.__version__)

for mod in ["GUI.AppGUI", "GUI.HotKey", "GUI.QGaugeTrayIcon", "GUI.QGauge", "GUI.QRadioButtonSet",
            "GUI.ThermalUnitWidget", "GUI.AppColors", "Backend.AWCCWmiWrapper", "Backend.AWCCThermal",
            "Backend.DetectHardware"]:
    __import__(mod)
print("imports: 10/10 ok")

from Backend.AWCCWmiWrapper import AWCCWmiWrapper as W
from Backend.AWCCThermal import AWCCThermal
from GUI.AppGUI import TCC_GUI


class FakeAwcc:
    """Records calls; returns `rc` for Thermal_Control (0 = success)."""
    def __init__(self, usttOk: bool = True):
        self.calls = []
        self.usttOk = usttOk

    def Thermal_Information(self, arg):
        self.calls.append(("Thermal_Information", arg)); return (0,)

    def GetFanSensors(self, arg):
        self.calls.append(("GetFanSensors", arg)); return (0,)

    def Thermal_Control(self, arg):
        self.calls.append(("Thermal_Control", arg))
        if (arg >> 8) == W.ThermalMode.Balanced.value and (arg & 0xFF) == 1:
            return (0,)  # plain Balanced is always accepted
        if (arg >> 8) == W._USTT_Balanced and (arg & 0xFF) == 1:
            return (0,) if self.usttOk else (1,)
        return (0,)


# --- bit packing -------------------------------------------------------------
f = FakeAwcc(); w = W(f)
w.GetSensorTemperature(1); w.GetFanRPM(0x31); w.SetAddonSpeedPercent(0x31, 100)
assert f.calls[:3] == [("Thermal_Information", (1 << 8) | 4),
                       ("Thermal_Information", (0x31 << 8) | 5),
                       ("Thermal_Control", (100 << 16) | (0x31 << 8) | 2)], f.calls
print("bit packing: ok")

# --- Balanced must never silently become Custom (upstream sent False -> mode 0)
f = FakeAwcc(usttOk=False); w = W(f)
w.ApplyThermalMode(W.ThermalMode.Balanced)
sent = [a for m, a in f.calls if m == "Thermal_Control"][-1]
assert sent == (W.ThermalMode.Balanced.value << 8) | 1, f"balanced fell back to {sent >> 8}"
assert (sent >> 8) != 0, "Balanced still sends Custom(0)"
print("balanced fallback: ok (mode 151, not 0)")

f = FakeAwcc(usttOk=True); w = W(f)
w.ApplyThermalMode(W.ThermalMode.Balanced)
sent = [a for m, a in f.calls if m == "Thermal_Control"][-1]
assert sent == (W._USTT_Balanced << 8) | 1, hex(sent)
print("balanced USTT patch: ok")

# --- invalid WMI answers -----------------------------------------------------
class Negative(FakeAwcc):
    def Thermal_Information(self, arg): return (-2,)
class Huge(FakeAwcc):
    def Thermal_Information(self, arg): return (0xFFFFFFFF,)
assert W(Negative()).GetFanRPMPercent(0x32) is None, "-2 must be treated as no data"
assert W(Huge()).GetSensorTemperature(1) is None, "0xFFFFFFFF must be treated as no data"
print("invalid WMI values: ok")

# --- temperature plausibility ------------------------------------------------
assert TCC_GUI._saneTemp(2) is None      # the bogus Dell reading
assert TCC_GUI._saneTemp(66) == 66
assert TCC_GUI._saneTemp(None) is None
assert TCC_GUI._saneTemp(200) is None
print("temperature guard: ok")

# --- COM cache helper is safe to call when there's nothing to clean ----------
from Backend.AWCCThermal import clearStaleComCache
assert isinstance(clearStaleComCache(), bool)
print("com cache helper: ok")

print("ALL CHECKS PASSED")
