"""FanCurve: temperature -> fan speed policy for the Auto thermal profile.

The owner's specification (2026-11-04):
    "Temp barar sathe sathe fan speed o bara, temp komar sathe sathe fan speed o koma.
     50 degree Celsius hole 3500 RPM, 80 ba 80+ hole full fan speed."

The firmware only accepts an additive speed offset in percent (`Thermal_Control` addon),
and the embedded controller still owns the real RPM curve, so this module works in
percent and documents the measured RPM equivalence for the G15 5530:

    64 %  ~= 3500 rpm   (measured at the 50 C anchor on this board)
    100 % ~= 5000+ rpm  (measured in G-mode)

Everything here is pure logic: no WMI, no Qt, no clock. The caller passes `now`, which
makes the write policy deterministic and testable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

MAX_PERCENT = 100
MIN_PERCENT = 0


@dataclass(frozen=True)
class CurvePoint:
    """One anchor of the fan curve."""

    temp_c: float
    percent: int


# Owner-specified anchors. 50 C -> ~64 % (about 3500 rpm on this board), 80 C -> 100 %.
DEFAULT_CURVE: Tuple[CurvePoint, ...] = (
    CurvePoint(50.0, 64),
    CurvePoint(80.0, 100),
)


def interpolate(temp_c: float, points: Sequence[CurvePoint] = DEFAULT_CURVE) -> int:
    """Piecewise-linear fan speed for `temp_c`, clamped to [0, 100].

    Below the first anchor the first value is used, above the last anchor the last value
    is used. This keeps the curve monotonic: a hotter machine never gets less cooling.
    """
    if not points:
        raise ValueError("curve needs at least one point")

    ordered = sorted(points, key=lambda p: p.temp_c)
    if temp_c <= ordered[0].temp_c:
        return _clamp(ordered[0].percent)
    if temp_c >= ordered[-1].temp_c:
        return _clamp(ordered[-1].percent)

    for left, right in zip(ordered, ordered[1:]):
        if left.temp_c <= temp_c <= right.temp_c:
            span = right.temp_c - left.temp_c
            if span <= 0:
                return _clamp(right.percent)
            ratio = (temp_c - left.temp_c) / span
            value = left.percent + ratio * (right.percent - left.percent)
            return _clamp(int(round(value)))

    return _clamp(ordered[-1].percent)


def _clamp(value: int) -> int:
    return max(MIN_PERCENT, min(MAX_PERCENT, int(value)))


class FanCurveDriver:
    """Decides *when* to write a curve target, per fan.

    Two rules keep the fans from rattling and the WMI bus from being hammered every tick:
      * deadband  - ignore changes smaller than `deadband_pct` points
      * rate limit - at most one write per fan per `min_interval_s` seconds

    A missing temperature never produces a write; the last applied target is kept, which
    means a sensor dropout cannot silently reduce cooling (INV-2, INV-6).
    """

    def __init__(self, deadband_pct: int = 3, min_interval_s: float = 1.5) -> None:
        self._deadband = max(0, int(deadband_pct))
        self._min_interval = max(0.0, float(min_interval_s))
        self._last_applied: dict[str, int] = {}
        self._last_write_at: dict[str, float] = {}

    def reset(self) -> None:
        self._last_applied.clear()
        self._last_write_at.clear()

    def last_applied(self, fan_key: str) -> Optional[int]:
        return self._last_applied.get(fan_key)

    def plan(
        self,
        fan_key: str,
        temp_c: Optional[float],
        now: float,
        points: Sequence[CurvePoint] = DEFAULT_CURVE,
    ) -> Optional[int]:
        """Return a percent to write, or None when the fan should be left alone."""
        if temp_c is None:
            return None

        target = interpolate(temp_c, points)
        previous = self._last_applied.get(fan_key)
        if previous is not None:
            # An identical target is nothing to do, whatever the deadband is.
            if target == previous:
                return None
            # Never step backwards into less cooling than the firmware already has.
            if abs(target - previous) < self._deadband:
                return None
            last_at = self._last_write_at.get(fan_key)
            if last_at is not None and (now - last_at) < self._min_interval:
                return None
        return target

    def confirm(self, fan_key: str, percent: int, now: float) -> None:
        """Record a write that the firmware accepted."""
        self._last_applied[fan_key] = percent
        self._last_write_at[fan_key] = now
