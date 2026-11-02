import sys, os, traceback
SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tcc-g15", "src"))
sys.path.insert(0, SRC)
sys.argv = ["tcc-g15.py"]

import PySide6
from PySide6 import QtCore, QtWidgets
print("PySide6", PySide6.__version__)
print("has QtCore.SIGNAL      :", hasattr(QtCore, "SIGNAL"))
print("has QObject.connect    :", hasattr(QtCore.QObject, "connect"))
print("has QMessageBox.exec_  :", hasattr(QtWidgets.QMessageBox, "exec_"))
print("has QSystemTrayIcon.ActivationReason:", hasattr(QtWidgets.QSystemTrayIcon, "ActivationReason"))

for mod in ["GUI.AppGui".replace("AppGui", "AppGUI"), "GUI.HotKey", "GUI.QGaugeTrayIcon",
            "GUI.QGauge", "GUI.QRadioButtonSet", "GUI.ThermalUnitWidget", "GUI.AppColors",
            "Backend.AWCCWmiWrapper", "Backend.AWCCThermal", "Backend.DetectHardware"]:
    try:
        __import__(mod)
        print("import ok  :", mod)
    except Exception as e:
        print("import FAIL:", mod, "->", type(e).__name__, e)

# arg encoding sanity check (no WMI needed)
from Backend.AWCCWmiWrapper import AWCCWmiWrapper as W
class Fake:
    def __init__(self): self.calls = []
    def Thermal_Information(self, arg):
        self.calls.append(("Thermal_Information", arg)); return (0,)
    def Thermal_Control(self, arg):
        self.calls.append(("Thermal_Control", arg)); return (0,)
    def GetFanSensors(self, arg):
        self.calls.append(("GetFanSensors", arg)); return (0,)
f = Fake(); w = W(f)
w.GetSensorTemperature(1); w.GetFanRPM(0x31); w.SetAddonSpeedPercent(0x31, 100)
w.ApplyThermalMode(W.ThermalMode.G_Mode)
print("encoded args:", [(m, hex(a)) for m, a in f.calls])
assert f.calls[0] == ("Thermal_Information", (1 << 8) | 4)
assert f.calls[1] == ("Thermal_Information", (0x31 << 8) | 5)
assert f.calls[2] == ("Thermal_Control", (100 << 16) | (0x31 << 8) | 2)
assert f.calls[3] == ("Thermal_Control", (0xAB << 8) | 1)
print("bit-packing self-check: PASS")
