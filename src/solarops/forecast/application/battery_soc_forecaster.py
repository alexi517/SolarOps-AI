"""BatterySocForecaster — Doc 8 §6.2 domain service.

Unlike Solar/Load, Battery SOC's baseline (brief §5) is an energy-balance
projection driven by *forecasted* generation and demand, not raw telemetry —
so this forecaster is handed the already-produced Solar and Load ``Forecast``
objects, reduces each to its average expected power over the projection
horizon, and packs that plus the current SOC into a ``FeatureSet``. It still
goes through the same ``ForecastModel`` interface and ``ForecastingService``
as the other two kinds — only how its features are assembled differs.
"""

from __future__ import annotations

from solarops.forecast.application.forecasting_service import ForecastingService
from solarops.forecast.domain.events import ForecastGenerated
from solarops.forecast.domain.exceptions import NoRegisteredModel
from solarops.forecast.domain.feature_set import FeatureSet
from solarops.forecast.domain.forecast import Forecast
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.ports import ModelRegistry
from solarops.forecast.infrastructure.config import ForecastConfig
from solarops.telemetry.domain.energy_state import EnergyState

__all__ = ["BatterySocForecaster"]


class BatterySocForecaster:
    def __init__(
        self,
        service: ForecastingService,
        registry: ModelRegistry,
        config: ForecastConfig,
    ) -> None:
        self._service = service
        self._registry = registry
        self._config = config

    def forecast(
        self,
        current: EnergyState,
        solar_forecast: Forecast,
        load_forecast: Forecast,
    ) -> tuple[Forecast, ForecastGenerated]:
        model = self._registry.get_current(ForecastKind.BATTERY_SOC)
        if model is None:
            raise NoRegisteredModel(ForecastKind.BATTERY_SOC)

        available = {
            "current_soc_pct": current.battery_soc.value,
            "avg_expected_solar_kw": _average_power(solar_forecast),
            "avg_expected_load_kw": _average_power(load_forecast),
        }
        values = {name: available[name] for name in self._config.battery_features}
        features = FeatureSet(kind=ForecastKind.BATTERY_SOC, as_of=current.timestamp, values=values)

        return self._service.generate(
            current.site_id,
            model,
            features,
            self._config.max_horizon_minutes,
            self._config.resolution_minutes,
        )


def _average_power(forecast: Forecast) -> float:
    values = [point.value.value for point in forecast.points]
    return sum(values) / len(values) if values else 0.0
