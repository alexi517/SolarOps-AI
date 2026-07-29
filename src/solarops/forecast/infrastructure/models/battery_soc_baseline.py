"""BatterySocBaseline — deterministic energy-balance projection (brief §5).

Projects SOC forward from forecasted generation minus forecasted demand
applied to current SOC with round-trip efficiency, exactly as specified.
Capacity and efficiency are site properties (wired from ``ForecastConfig``,
itself populated from the real ``SiteConfig`` at the platform composition
root), not per-call features — only the current SOC and the average expected
solar/load come from the ``FeatureSet``.
"""

from __future__ import annotations

from datetime import timedelta

from solarops.forecast.domain.feature_set import FeatureSet
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.forecast_point import ForecastPoint
from solarops.shared_kernel import StateOfCharge

__all__ = ["BatterySocBaseline"]


class BatterySocBaseline:
    name = "battery-soc-baseline"
    version = "v1"
    kind = ForecastKind.BATTERY_SOC

    def __init__(
        self,
        capacity_kwh: float = 200.0,
        round_trip_efficiency: float = 0.92,
        resolution_minutes: int = 15,
    ) -> None:
        self.capacity_kwh = capacity_kwh
        self.round_trip_efficiency = round_trip_efficiency
        self.resolution_minutes = resolution_minutes

    def predict(self, features: FeatureSet, horizon_minutes: int) -> list[ForecastPoint]:
        current_soc_pct = features.values.get("current_soc_pct", 50.0)
        avg_solar_kw = features.values.get("avg_expected_solar_kw", 0.0)
        avg_load_kw = features.values.get("avg_expected_load_kw", 0.0)
        net_power_kw = avg_solar_kw - avg_load_kw

        points: list[ForecastPoint] = []
        elapsed = 0
        while elapsed <= horizon_minutes:
            timestamp = features.as_of + timedelta(minutes=elapsed)
            energy_kwh = net_power_kw * (elapsed / 60.0)
            if energy_kwh > 0:
                # Charging: round-trip losses reduce what actually gets stored.
                energy_kwh *= self.round_trip_efficiency
            soc_change_pct = (
                (energy_kwh / self.capacity_kwh) * 100.0 if self.capacity_kwh > 0 else 0.0
            )
            soc_pct = min(100.0, max(0.0, current_soc_pct + soc_change_pct))
            points.append(
                ForecastPoint(timestamp=timestamp, value=StateOfCharge(round(soc_pct, 2)))
            )
            elapsed += self.resolution_minutes
        return points
