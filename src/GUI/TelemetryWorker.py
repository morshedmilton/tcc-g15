import ctypes
from ctypes import wintypes
import time
from typing import Optional
from PySide6 import QtCore

from Backend.TelemetryTypes import TelemetrySnapshot

class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ('ACLineStatus', wintypes.BYTE),
        ('BatteryFlag', wintypes.BYTE),
        ('BatteryLifePercent', wintypes.BYTE),
        ('SystemStatusFlag', wintypes.BYTE),
        ('BatteryLifeTime', wintypes.DWORD),
        ('BatteryFullLifeTime', wintypes.DWORD),
    ]

def queryAcPowerStatus() -> Optional[bool]:
    """Returns True if on AC power, False if on battery, None if unknown."""
    try:
        status = SYSTEM_POWER_STATUS()
        if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
            if status.ACLineStatus == 0:
                return False
            elif status.ACLineStatus == 1:
                return True
    except Exception:
        pass
    return None

def sanitizeTemperature(temp: Optional[int]) -> Optional[int]:
    """Clamps temperature readings to reasonable physical hardware bounds (0°C to 125°C)."""
    if temp is None:
        return None
    try:
        t = int(temp)
        if 0 <= t <= 125:
            return t
    except (ValueError, TypeError):
        pass
    return None


class TelemetryWorker(QtCore.QObject):
    """Background hardware telemetry worker running in a dedicated QThread.
    
    Decouples Dell ACPI WMI queries and NVIDIA NVML driver polls from the Qt GUI main thread.
    Emits TelemetrySnapshot via Qt queued signals to guarantee 0ms UI lockup.
    """
    telemetryReady = QtCore.Signal(object)  # Emits TelemetrySnapshot
    telemetryError = QtCore.Signal(str)     # Emits error description if polling fails

    def __init__(self, awcc=None, gpuTemp=None, pollingIntervalMs: int = 2000) -> None:
        super().__init__()
        self._awcc = awcc
        self._gpuTemp = gpuTemp
        self._pollingIntervalMs = pollingIntervalMs
        self._timer: Optional[QtCore.QTimer] = None
        self._running = True
        self._comInitialized = False

    @QtCore.Slot()
    def start(self) -> None:
        """Initializes COM apartment and starts periodic sensor polling on worker thread."""
        try:
            import pythoncom
            pythoncom.CoInitialize()
            self._comInitialized = True
        except Exception:
            pass

        if self._gpuTemp is None:
            try:
                from Backend.GpuTemp import GpuTemperature
                self._gpuTemp = GpuTemperature()
            except Exception:
                pass

        if self._awcc is None:
            try:
                from Backend.AWCCThermal import AWCCThermal
                self._awcc = AWCCThermal()
            except Exception as ex:
                self.telemetryError.emit(f"Failed to instantiate AWCCThermal in worker: {ex}")

        self._running = True
        self._timer = QtCore.QTimer()
        self._timer.setInterval(self._pollingIntervalMs)
        self._timer.timeout.connect(self.pollOnce)
        self._timer.start()

        # Immediate first reading upon worker thread startup
        self.pollOnce()

    @QtCore.Slot()
    def pollOnce(self, emitSignal: bool = True) -> Optional[TelemetrySnapshot]:
        """Executes a single hardware reading cycle and emits TelemetrySnapshot."""
        if not self._running:
            return None

        try:
            # 1. GPU Temperature (NVML driver preferred, fallback to Dell WMI sensor)
            nvmlGpu = self._gpuTemp.read() if self._gpuTemp is not None else None
            rawGpu = nvmlGpu
            if rawGpu is None and self._awcc is not None:
                try:
                    rawGpu = self._awcc.getFanRelatedTemp(self._awcc.GPUFanIdx)
                except Exception:
                    rawGpu = None
            gpuTemp = sanitizeTemperature(rawGpu)

            # 2. GPU Fan RPM
            gpuRpm = None
            if self._awcc is not None:
                try:
                    gpuRpm = self._awcc.getFanRPM(self._awcc.GPUFanIdx)
                except Exception:
                    gpuRpm = None

            # 3. CPU Temperature (Dell WMI sensor)
            rawCpu = None
            if self._awcc is not None:
                try:
                    rawCpu = self._awcc.getFanRelatedTemp(self._awcc.CPUFanIdx)
                except Exception:
                    rawCpu = None
            cpuTemp = sanitizeTemperature(rawCpu)

            # 4. CPU Fan RPM
            cpuRpm = None
            if self._awcc is not None:
                try:
                    cpuRpm = self._awcc.getFanRPM(self._awcc.CPUFanIdx)
                except Exception:
                    cpuRpm = None

            # 5. AC Power Line Status
            acPower = queryAcPowerStatus()

            snapshot = TelemetrySnapshot(
                cpu_temp=cpuTemp,
                gpu_temp=gpuTemp,
                cpu_rpm=cpuRpm,
                gpu_rpm=gpuRpm,
                is_ac_power=acPower,
                timestamp=time.time()
            )
            if emitSignal:
                self.telemetryReady.emit(snapshot)
            return snapshot
        except Exception as ex:
            if emitSignal:
                self.telemetryError.emit(f"Telemetry poll exception: {ex}")
            return None

    @QtCore.Slot(int)
    def setInterval(self, intervalMs: int) -> None:
        """Dynamically adjusts polling frequency (e.g. 2000ms foreground vs 5000ms minimized)."""
        self._pollingIntervalMs = intervalMs
        if self._timer is not None and self._timer.interval() != intervalMs:
            self._timer.setInterval(intervalMs)

    @QtCore.Slot()
    def stop(self) -> None:
        """Stops the timer and cleanly uninitializes COM on the worker thread."""
        self._running = False
        if self._timer is not None:
            self._timer.stop()
            self._timer = None

        if self._comInitialized:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass
            self._comInitialized = False
