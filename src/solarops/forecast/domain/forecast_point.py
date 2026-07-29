"""ForecastPoint — VO: one predicted value at one point in time (Doc 8 §6.2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from solarops.shared_kernel import Power, StateOfCharge

__all__ = ["ForecastPoint"]


@dataclass(frozen=True, slots=True)
class ForecastPoint:
    """One predicted (timestamp, value) pair, with an optional prediction interval.

    ``value`` is ``Power`` for solar/load, ``StateOfCharge`` for battery — the
    same physical-quantity types Telemetry and Simulation use, so a forecast
    and an actual reading are directly comparable.
    """

    timestamp: datetime
    value: Power | StateOfCharge
    interval_low: float | None = None
    interval_high: float | None = None
