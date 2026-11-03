import time
from enum import Enum
from typing import Optional, Tuple
from wmi import _wmi_object # type: ignore

class AWCCWmiWrapper:
    SENSOR_ID_FIRST = 0x01
    SENSOR_ID_LAST = 0x30
    FAN_ID_FIRST = 0x31
    FAN_ID_LAST = 0x63

    class ThermalMode(Enum):
        Custom = 0
        Balanced = 0x97
        G_Mode = 0xAB
        Quiet = 0x96
        Performance = 0x98

    # Firmware families disagree on the ids. Verified on a G15 5530 (BIOS 1.36.0):
    # the plain 150/152/153 are rejected and only the USTT variants answer 0, while
    # older boards accept the plain ids. Probe USTT first, then the plain value, and
    # cache the winner per mode.
    _USTT_IDS = {ThermalMode.Balanced: 0xA0, ThermalMode.Performance: 0xA1, ThermalMode.Quiet: 0xA3}

    def __init__(self, awcc: _wmi_object) -> None:
        self._awcc = awcc
        self._resolvedModes: dict = {}

    def GetSensorTemperature(self, sensorId: int) -> Optional[int]:
        if not (sensorId in range(self.SENSOR_ID_FIRST, self.SENSOR_ID_LAST + 1)): return None
        arg = ((sensorId & 0xFF) << 8) | 4
        return self._call('Thermal_Information', arg)

    def GetFanRPMPercent(self, fanId: int) -> Optional[int]:
        if not (fanId in range(self.FAN_ID_FIRST, self.FAN_ID_LAST + 1)): return None
        arg = ((fanId & 0xFF) << 8) | 6
        return self._call('Thermal_Information', arg)

    def GetFanRPM(self, fanId: int) -> Optional[int]:
        if not (fanId in range(self.FAN_ID_FIRST, self.FAN_ID_LAST + 1)): return None
        arg = ((fanId & 0xFF) << 8) | 5
        return self._call('Thermal_Information', arg)


    def GetFanRelatedSensorsCountById(self, fanId: int) -> Optional[int]:
        if not (fanId in range(self.FAN_ID_FIRST, self.FAN_ID_LAST + 1)): return None
        arg = ((fanId & 0xFF) << 8) | 1
        return self._call('GetFanSensors', arg)

    def GetFanRelatdSensorsById(self, fanId: int, sensorIndex: int) -> Optional[int]:
        if not (fanId in range(self.FAN_ID_FIRST, self.FAN_ID_LAST + 1)): return None
        arg = ((sensorIndex & 0xFF) << 16) | ((fanId & 0xFF) << 8) | 2
        return self._call('GetFanSensors', arg)

    def GetFanIdsAndRelatedSensorsCount(self) -> list[Tuple[int, int]]:
        res: list[Tuple[int, int]] = []
        for idx in range(self.FAN_ID_FIRST, self.FAN_ID_LAST + 1):
            count = self.GetFanRelatedSensorsCountById(idx)
            if count is not None and count > 0: res.append((idx, count))
        return res

    def GetFanIdsAndRelatedSensorsIds(self) -> list[Tuple[int, Tuple[int, ...]]]:
        return [ 
            (
                fanId, 
                tuple(
                    id for id in (
                        self.GetFanRelatdSensorsById(fanId, idx) for idx in range(sensorCount)
                    ) if id is not None
                )
            ) for fanId, sensorCount in self.GetFanIdsAndRelatedSensorsCount() 
        ]


    def ApplyThermalMode(self, mode: ThermalMode) -> bool:
        if not isinstance(mode, self.ThermalMode):
            raise Exception('Invalid argument: mode is not instance of ThermalMode')

        cached = self._resolvedModes.get(mode)
        if cached is not None:
            if cached is False:
                return False
            ok = self._Thermal_Control(cached)
            if not ok:
                time.sleep(0.25)
                ok = self._Thermal_Control(cached)
            return ok

        # First use of this mode on this firmware: the probe call is itself the apply,
        # so a 0 answer means the mode is now set and there is nothing left to do.
        for candidate in [c for c in (self._USTT_IDS.get(mode), mode.value) if c is not None]:
            ok = self._Thermal_Control(candidate)
            if not ok:
                time.sleep(0.25)
                ok = self._Thermal_Control(candidate)
            if ok:
                self._resolvedModes[mode] = candidate
                print(f'Mode {mode.name} resolved to {hex(candidate)}')
                return True

        self._resolvedModes[mode] = False
        print(f'Mode {mode.name} is not supported by this firmware')
        return False

    def SetAddonSpeedPercent(self, fanId: int, speed: int) -> bool:
        if not (fanId in range(self.FAN_ID_FIRST, self.FAN_ID_LAST + 1)): return False
        if speed > 0xFF: speed = 0xFF
        arg = ((speed & 0xFF) << 16) | ((fanId & 0xFF) << 8) | 2
        return self._call('Thermal_Control', arg) == 0

    def _Thermal_Control(self, arg: int) -> bool:
        arg = ((arg & 0xFF) << 8) | 1
        return self._call('Thermal_Control', arg) == 0
        
    def _call(self, method: str, arg: int) -> Optional[int]:
        if not hasattr(self._awcc, method) or not callable(getattr(self._awcc, method)):
            return None
        val: int = getattr(self._awcc, method)(arg)[0]
        # G15 5530 answers -2 (not just -1) for unsupported queries like GetFanRPMPercent
        if not isinstance(val, int) or val < 0 or val == 0xFFFFFFFF:
            return None
        return val
