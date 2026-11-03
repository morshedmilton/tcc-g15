from dataclasses import dataclass
from typing import Optional
import time

@dataclass(frozen=True)
class TelemetrySnapshot:
    """Immutable data transfer object representing a point-in-time hardware telemetry reading.
    
    Used to safely pass telemetry across thread boundaries from TelemetryWorker to GUI widgets.
    """
    cpu_temp: Optional[int]
    gpu_temp: Optional[int]
    cpu_rpm: Optional[int]
    gpu_rpm: Optional[int]
    is_ac_power: Optional[bool]
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            object.__setattr__(self, 'timestamp', time.time())
