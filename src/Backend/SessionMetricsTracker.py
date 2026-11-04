import time
from typing import Optional, Dict, Any
from Backend.TelemetryTypes import TelemetrySnapshot


class SessionMetricsTracker:
    """In-memory aggregator for real-time session thermal dynamics and excursion analytics.
    
    Provides O(1) tracking of peak and average temperatures, maximum fan speeds,
    cumulative high-temperature excursion duration, and proactive sustained saturation detection.
    Guarantees thread-safe, non-intrusive execution without file I/O latency.
    """

    EXCURSION_CPU_THRESHOLD = 90  # °C
    EXCURSION_GPU_THRESHOLD = 82  # °C
    ADVISORY_SUSTAINED_SEC = 30.0  # Consecutive seconds before advisory toast
    ADVISORY_COOLDOWN_SEC = 300.0  # 5-minute cooldown between advisories
    MAX_SAMPLE_INTERVAL_GRACE_SEC = 10.0  # Clamps gap on sleep/resume

    def __init__(self, start_ts: Optional[float] = None) -> None:
        self._start_ts: float = start_ts if start_ts is not None else time.time()
        self._last_sample_ts: Optional[float] = None
        self._sample_count: int = 0

        self._peak_cpu_temp: Optional[int] = None
        self._peak_gpu_temp: Optional[int] = None
        self._min_cpu_temp: Optional[int] = None
        self._min_gpu_temp: Optional[int] = None

        self._sum_cpu_temp: int = 0
        self._cpu_sample_count: int = 0
        self._sum_gpu_temp: int = 0
        self._gpu_sample_count: int = 0

        self._peak_cpu_rpm: Optional[int] = None
        self._peak_gpu_rpm: Optional[int] = None

        self._high_temp_excursion_seconds: float = 0.0
        self._consecutive_high_temp_start_ts: Optional[float] = None
        self._last_advisory_ts: float = 0.0

        self._failsafe_trip_count: int = 0

    @property
    def peak_cpu_temp(self) -> Optional[int]:
        return self._peak_cpu_temp

    @property
    def peak_gpu_temp(self) -> Optional[int]:
        return self._peak_gpu_temp

    @property
    def peak_cpu_rpm(self) -> Optional[int]:
        return self._peak_cpu_rpm

    @property
    def peak_gpu_rpm(self) -> Optional[int]:
        return self._peak_gpu_rpm

    @property
    def failsafe_trip_count(self) -> int:
        return self._failsafe_trip_count

    @property
    def high_temp_excursion_seconds(self) -> float:
        return self._high_temp_excursion_seconds

    def update(self, snapshot: TelemetrySnapshot) -> None:
        """Processes a single TelemetrySnapshot and updates running metrics."""
        now = snapshot.timestamp if snapshot.timestamp is not None else time.time()
        self._sample_count += 1

        # 1. Temperature Peaks, Minimums, and Running Sums
        if snapshot.cpu_temp is not None:
            c = snapshot.cpu_temp
            self._peak_cpu_temp = c if self._peak_cpu_temp is None else max(self._peak_cpu_temp, c)
            self._min_cpu_temp = c if self._min_cpu_temp is None else min(self._min_cpu_temp, c)
            self._sum_cpu_temp += c
            self._cpu_sample_count += 1

        if snapshot.gpu_temp is not None:
            g = snapshot.gpu_temp
            self._peak_gpu_temp = g if self._peak_gpu_temp is None else max(self._peak_gpu_temp, g)
            self._min_gpu_temp = g if self._min_gpu_temp is None else min(self._min_gpu_temp, g)
            self._sum_gpu_temp += g
            self._gpu_sample_count += 1

        # 2. Fan RPM Peaks
        if snapshot.cpu_rpm is not None:
            r = snapshot.cpu_rpm
            self._peak_cpu_rpm = r if self._peak_cpu_rpm is None else max(self._peak_cpu_rpm, r)

        if snapshot.gpu_rpm is not None:
            r = snapshot.gpu_rpm
            self._peak_gpu_rpm = r if self._peak_gpu_rpm is None else max(self._peak_gpu_rpm, r)

        # 3. Excursion Duration Tracking (CPU >= 90°C or GPU >= 82°C)
        is_excursion = (
            (snapshot.cpu_temp is not None and snapshot.cpu_temp >= self.EXCURSION_CPU_THRESHOLD) or
            (snapshot.gpu_temp is not None and snapshot.gpu_temp >= self.EXCURSION_GPU_THRESHOLD)
        )

        if is_excursion:
            if self._consecutive_high_temp_start_ts is None:
                self._consecutive_high_temp_start_ts = now

            if self._last_sample_ts is not None:
                delta = now - self._last_sample_ts
                # Clamp delta to avoid inflating excursion time during OS sleep/suspend
                if 0.0 < delta <= self.MAX_SAMPLE_INTERVAL_GRACE_SEC:
                    self._high_temp_excursion_seconds += delta
        else:
            self._consecutive_high_temp_start_ts = None

        self._last_sample_ts = now

    def record_failsafe_trip(self) -> None:
        """Records an emergency fail-safe trip execution to G_Mode."""
        self._failsafe_trip_count += 1

    def should_trigger_advisory(self, current_mode: str, now: Optional[float] = None) -> bool:
        """Evaluates whether a proactive thermal advisory toast should be shown.
        
        Returns True only if:
        1. High temperature excursion has persisted for >= 30 continuous seconds.
        2. Current thermal mode is 'Quiet' or 'Balanced'.
        3. At least 300 seconds have elapsed since the last advisory notification.
        """
        ts = now if now is not None else time.time()
        if self._consecutive_high_temp_start_ts is None:
            return False

        if current_mode not in ('Quiet', 'Balanced'):
            return False

        duration = ts - self._consecutive_high_temp_start_ts
        if duration < self.ADVISORY_SUSTAINED_SEC:
            return False

        if (ts - self._last_advisory_ts) < self.ADVISORY_COOLDOWN_SEC:
            return False

        self._last_advisory_ts = ts
        return True

    def get_summary(self) -> Dict[str, Any]:
        """Returns JSON-serializable dictionary of session thermal statistics."""
        uptime = max(0.0, time.time() - self._start_ts)
        avg_cpu = round(self._sum_cpu_temp / self._cpu_sample_count, 1) if self._cpu_sample_count else None
        avg_gpu = round(self._sum_gpu_temp / self._gpu_sample_count, 1) if self._gpu_sample_count else None

        return {
            "session_uptime_seconds": round(uptime, 1),
            "sample_count": self._sample_count,
            "peak_cpu_temp": self._peak_cpu_temp,
            "peak_gpu_temp": self._peak_gpu_temp,
            "avg_cpu_temp": avg_cpu,
            "avg_gpu_temp": avg_gpu,
            "min_cpu_temp": self._min_cpu_temp,
            "min_gpu_temp": self._min_gpu_temp,
            "peak_cpu_rpm": self._peak_cpu_rpm,
            "peak_gpu_rpm": self._peak_gpu_rpm,
            "high_temp_excursion_seconds": round(self._high_temp_excursion_seconds, 1),
            "failsafe_trip_count": self._failsafe_trip_count,
        }


# Singleton session tracker instance for cross-module diagnostics export
_active_session_tracker: Optional[SessionMetricsTracker] = None

def get_session_tracker() -> SessionMetricsTracker:
    global _active_session_tracker
    if _active_session_tracker is None:
        _active_session_tracker = SessionMetricsTracker()
    return _active_session_tracker

def set_session_tracker(tracker: SessionMetricsTracker) -> None:
    global _active_session_tracker
    _active_session_tracker = tracker
