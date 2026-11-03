"""Real GPU temperature from the NVIDIA driver (NVML).

The Dell WMI sensor is the known source of the 2-3 C bogus reading (#9). NVML reads the
driver directly and answered plausibly on this board (61 C while the WMI sensor said 64 C).
Everything degrades to None when the driver/NVML is missing, so the caller can fall back.
"""
from typing import Optional


class GpuTemperature:
    def __init__(self) -> None:
        self._nvml = None
        self._handle = None
        try:
            import pynvml  # type: ignore
            pynvml.nvmlInit()
            self._nvml = pynvml
            self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        except Exception as ex:
            print(f'NVML unavailable: {type(ex).__name__}')

    @property
    def available(self) -> bool:
        return self._handle is not None

    def read(self) -> Optional[int]:
        if self._handle is None:
            return None
        try:
            return int(self._nvml.nvmlDeviceGetTemperature(self._handle, self._nvml.NVML_TEMPERATURE_GPU))
        except Exception:
            return None

    def shutdown(self) -> None:
        if self._nvml is not None:
            try:
                self._nvml.nvmlShutdown()
            except Exception:
                pass
            self._handle = None
