import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional, NewType
from Backend.AWCCWmiWrapper import AWCCWmiWrapper
from wmi import WMI # type: ignore

def clearStaleComCache() -> bool:
    """win32com caches generated wrappers in %TEMP%\\gen_py. After AWCC is uninstalled that
    cache can point at a dead typelib, and the WMI class stops loading at all (issue #64)."""
    cache = Path(tempfile.gettempdir()) / 'gen_py'
    if not cache.is_dir():
        return False
    shutil.rmtree(cache, ignore_errors=True)
    return True

class NoAWCCWMIClass(Exception):
    def __init__(self) -> None:
        super().__init__("AWCC WMI class not found in the system")

class CannotInstAWCCWMI(Exception):
    def __init__(self) -> None:
        super().__init__("Couldn't instantiate AWCC WMI class")

class AWCCThermal:
    Mode = AWCCWmiWrapper.ThermalMode
    ModeType = NewType("ModeType", AWCCWmiWrapper.ThermalMode)
    CPUFanIdx = 0
    GPUFanIdx = 1
    CONNECT_RETRIES = 5
    CONNECT_RETRY_DELAY_SEC = 1.5
    # Errors waiting cannot fix: no admin rights, or no AWCC ACPI device on this machine
    NOT_RETRYABLE = ('x_access_denied', 'x_wmi_invalid_namespace')

    def __init__(self, awcc: Optional[AWCCWmiWrapper] = None) -> None:
        if awcc is None:
            awcc = self._instantiateWithRetry(self._awccClassWithRetry())
        self._awcc = awcc
        self._fanIdsAndRelatedSensorsIds = self._awcc.GetFanIdsAndRelatedSensorsIds()
        self._fanIds = [ id for id, _ in self._fanIdsAndRelatedSensorsIds ]
        self._sensorIds = [ id for _, ids in self._fanIdsAndRelatedSensorsIds for id in ids ]

    def getAllTemp(self) -> list[Optional[int]]:
        return [ self._awcc.GetSensorTemperature(sensorId) for sensorId in self._sensorIds ]

    def getAllFanRPM(self) -> list[Optional[int]]:
        return [ self._awcc.GetFanRPM(fanId) for fanId in self._fanIds ]

    def setAllFanSpeed(self, speed: int) -> bool:
        res = True
        for fanId in self._fanIds:
            if not self._awcc.SetAddonSpeedPercent(fanId, speed):
                res = False
        return res


    def getFanRelatedTemp(self, fanIdx: int) -> Optional[int]:
        if fanIdx >= len(self._fanIdsAndRelatedSensorsIds):
            return None
        return self._awcc.GetSensorTemperature(self._fanIdsAndRelatedSensorsIds[fanIdx][1][0])

    def getFanRPM(self, fanIdx: int) -> Optional[int]:
        if fanIdx >= len(self._fanIdsAndRelatedSensorsIds):
            return None
        return self._awcc.GetFanRPM(self._fanIdsAndRelatedSensorsIds[fanIdx][0])

    def setFanSpeed(self, fanIdx: int, speed: int) -> bool:
        if fanIdx >= len(self._fanIdsAndRelatedSensorsIds):
            return False
        return self._awcc.SetAddonSpeedPercent(self._fanIdsAndRelatedSensorsIds[fanIdx][0], speed)

    def setMode(self, mode: ModeType) -> bool:
        return self._awcc.ApplyThermalMode(mode)

    @classmethod
    def _isNotRetryable(cls, ex: Exception) -> bool:
        name = type(ex).__name__
        return any(k in name for k in cls.NOT_RETRYABLE) or 'Access is denied' in str(ex)

    @classmethod
    def _awccClassWithRetry(cls):
        # The AWCC service can still be starting when we run at boot (#90), so retry;
        # a stale COM cache is the other known cause (#64) and is cleared once.
        lastEx: Optional[Exception] = None
        for attempt in range(cls.CONNECT_RETRIES):
            try:
                return WMI(namespace="root\\WMI").AWCCWmiMethodFunction
            except Exception as ex:
                lastEx = ex
                print(ex)
                if cls._isNotRetryable(ex):
                    break
                if attempt == 0 and clearStaleComCache():
                    print('Cleared stale COM cache, retrying')
                    continue
                time.sleep(cls.CONNECT_RETRY_DELAY_SEC)
        raise NoAWCCWMIClass() from lastEx

    @classmethod
    def _instantiateWithRetry(cls, awccClass) -> AWCCWmiWrapper:
        lastEx: Optional[Exception] = None
        for attempt in range(cls.CONNECT_RETRIES):
            try:
                return AWCCWmiWrapper(awccClass()[0])
            except Exception as ex:
                lastEx = ex
                print(ex)
                if cls._isNotRetryable(ex):
                    break
                if attempt == 0 and clearStaleComCache():
                    print('Cleared stale COM cache, retrying')
                    continue
                time.sleep(cls.CONNECT_RETRY_DELAY_SEC)
        raise CannotInstAWCCWMI() from lastEx
