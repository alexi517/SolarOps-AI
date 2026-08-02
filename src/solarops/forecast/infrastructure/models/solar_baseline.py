"""SolarBaseline — deterministic clear-sky curve, the V1 default (brief §4).

A ``ForecastModel`` with no ``fit`` — the baseline the system runs end-to-end
with before any ML model passes the gate. Reimplements (does not import) the
same clear-sky bell-curve shape as
``simulation.domain.models.weather._clear_sky_irradiance`` — Forecast may not
depend on Simulation (brief §8), so the curve is re-derived here from first
principles (sunrise/sunset bounded sine bell), not shared code.
"""

from __future__ import annotations

import math
from datetime import timedelta

from solarops.forecast.domain.feature_set import FeatureSet
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.forecast_point import ForecastPoint
from solarops.shared_kernel import Power

__all__ = ["SolarBaseline"]

_PEAK_IRRADIANCE_W_M2 = 1000.0
_SUNRISE_HOUR = 6.0
_SUNSET_HOUR = 18.0
# Kept in sync with simulation.domain.models.weather.SITE_UTC_OFFSET_HOURS —
# this site is in Nigeria (WAT, UTC+1); the timestamps this model receives
# are UTC, so the same offset is needed here to predict the same day/night
# boundary the twin's real solar output actually follows. Duplicated, not
# imported, per this file's own docstring (Forecast may not depend on
# Simulation) — if the twin's offset ever changes, this constant must too.
_SITE_UTC_OFFSET_HOURS = 1.0


def _clear_sky_fraction(hour_of_day: float) -> float:
    if hour_of_day <= _SUNRISE_HOUR or hour_of_day >= _SUNSET_HOUR:
        return 0.0
    daylight_fraction = (hour_of_day - _SUNRISE_HOUR) / (_SUNSET_HOUR - _SUNRISE_HOUR)
    return math.sin(math.pi * daylight_fraction)


class SolarBaseline:
    """Clear-sky bell curve scaled by the current cloud-cover reading."""

    name = "solar-baseline"
    version = "v1"
    kind = ForecastKind.SOLAR_GENERATION

    def __init__(self, capacity_kw: float = 100.0, resolution_minutes: int = 15) -> None:
        self.capacity_kw = capacity_kw
        self.resolution_minutes = resolution_minutes

    def predict(self, features: FeatureSet, horizon_minutes: int) -> list[ForecastPoint]:
        cloud_cover_pct = features.values.get("cloud_cover_pct", 0.0)
        cloud_factor = 1.0 - 0.75 * (cloud_cover_pct / 100.0)

        points: list[ForecastPoint] = []
        elapsed = 0
        while elapsed <= horizon_minutes:
            timestamp = features.as_of + timedelta(minutes=elapsed)
            utc_hour_of_day = timestamp.hour + timestamp.minute / 60.0
            hour_of_day = (utc_hour_of_day + _SITE_UTC_OFFSET_HOURS) % 24.0
            irradiance_fraction = _clear_sky_fraction(hour_of_day)
            power_kw = self.capacity_kw * irradiance_fraction * cloud_factor
            value = Power(round(max(0.0, power_kw), 3))
            points.append(ForecastPoint(timestamp=timestamp, value=value))
            elapsed += self.resolution_minutes
        return points
