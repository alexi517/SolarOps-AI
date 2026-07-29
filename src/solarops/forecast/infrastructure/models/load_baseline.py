"""LoadBaseline — deterministic occupancy-curve model, the V1 default (brief §4).

Reimplements (does not import) the same occupancy-curve shape as
``simulation.domain.models.building_load._occupancy_factor`` — Forecast may
not depend on Simulation (brief §8). Since it has no access to the site's
configured baseline/peak load (that lives in Simulation's ``SiteConfig``), it
scales the curve by the peak load actually observed over the
``HistoricalDataSource`` lookback window (``building_load_peak_observed_kw``,
from ``feature_engineering.py``) rather than inferring capacity from a single
instantaneous reading — dividing the current reading by the current occupancy
factor was tried first and is numerically unstable whenever "now" falls near
the dawn/dusk transition, where occupancy is small and the implied capacity
blows up.
"""

from __future__ import annotations

import math
from datetime import timedelta

from solarops.forecast.domain.feature_set import FeatureSet
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.forecast_point import ForecastPoint
from solarops.shared_kernel import Power

__all__ = ["LoadBaseline"]

_OCCUPANCY_START_HOUR = 6.0
_OCCUPANCY_END_HOUR = 22.0
_NIGHT_LOAD_FRACTION = 0.05
_WEEKEND_LOAD_MULTIPLIER = 0.4


def _occupancy_factor(hour_of_day: float) -> float:
    if hour_of_day <= _OCCUPANCY_START_HOUR or hour_of_day >= _OCCUPANCY_END_HOUR:
        return _NIGHT_LOAD_FRACTION
    daylight_fraction = (hour_of_day - _OCCUPANCY_START_HOUR) / (
        _OCCUPANCY_END_HOUR - _OCCUPANCY_START_HOUR
    )
    return max(_NIGHT_LOAD_FRACTION, math.sin(math.pi * daylight_fraction))


class LoadBaseline:
    """Occupancy curve scaled by the peak load observed over recent history."""

    name = "load-baseline"
    version = "v1"
    kind = ForecastKind.BUILDING_LOAD

    def __init__(self, resolution_minutes: int = 15) -> None:
        self.resolution_minutes = resolution_minutes

    def predict(self, features: FeatureSet, horizon_minutes: int) -> list[ForecastPoint]:
        current_load_kw = features.values.get("building_load_kw", 0.0)
        implied_capacity_kw = features.values.get(
            "building_load_peak_observed_kw", current_load_kw
        )

        points: list[ForecastPoint] = []
        elapsed = 0
        while elapsed <= horizon_minutes:
            timestamp = features.as_of + timedelta(minutes=elapsed)
            hour_of_day = timestamp.hour + timestamp.minute / 60.0
            occupancy = _occupancy_factor(hour_of_day)
            if timestamp.weekday() >= 5:
                occupancy *= _WEEKEND_LOAD_MULTIPLIER
            load_kw = max(0.0, implied_capacity_kw * occupancy)
            points.append(ForecastPoint(timestamp=timestamp, value=Power(round(load_kw, 3))))
            elapsed += self.resolution_minutes
        return points
