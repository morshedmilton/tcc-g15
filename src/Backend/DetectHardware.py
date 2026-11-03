import os
from typing import Optional
from wmi import WMI # type: ignore

# Models this fork is willing to write thermal settings on. Matched as substrings against
# the SMBIOS "Manufacturer Model" string. Anything else is refused unless the user opts
# in with TCC_ALLOW_UNSUPPORTED=1 - an unverified board can answer different mode ids.
SUPPORTED_MODELS = (
    'G15 5511', 'G15 5515', 'G15 5520', 'G15 5525', 'G15 5530', 'G15 5535', 'G15 5590',
    'G3 3590', 'G3 3500', 'm16 R1', '16X Aurora', 'AA18250',
)
ALLOW_UNSUPPORTED_ENV = 'TCC_ALLOW_UNSUPPORTED'

class DetectHardware:
    CPUFanIdx = 0
    GPUFanIdx = 1

    def __init__(self) -> None:
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass
        self._wmi = WMI()

    def getModelName(self) -> Optional[str]:
        try:
            cs = self._wmi.Win32_ComputerSystem()[0]
            return f'{cs.Manufacturer} {cs.Model}'.strip()
        except Exception:
            return None

    @staticmethod
    def isSupportedModel(model: Optional[str]) -> bool:
        if not model:
            return False
        return any(p.lower() in model.lower() for p in SUPPORTED_MODELS)

    @staticmethod
    def isUnsupportedAllowed() -> bool:
        return os.environ.get(ALLOW_UNSUPPORTED_ENV, '') not in ('', '0')

    def getHardwareName(self, fanIdx: int) -> Optional[str]:
        try:
            if fanIdx == self.CPUFanIdx:
                wmiClass = self._wmi.Win32_Processor
                wmiInst = wmiClass()[0]
                return wmiInst.Name.strip() if hasattr(wmiInst, 'Name') else None
            elif fanIdx == self.GPUFanIdx:
                wmiClass = self._wmi.Win32_VideoController
                controllers = wmiClass()
                if not controllers:
                    return None
                wmiInst = max(controllers, key=lambda inst: inst.AdapterRAM & 0xFFFFFFFF if hasattr(inst, 'AdapterRAM') and isinstance(inst.AdapterRAM, int) else 0) # Assume the one with the largest memory is the main GPU
                return wmiInst.Name.strip() if hasattr(wmiInst, 'Name') else None
            else:
                return None
        except Exception:
            return None