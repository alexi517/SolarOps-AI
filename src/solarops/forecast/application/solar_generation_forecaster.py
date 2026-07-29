"""SolarGenerationForecaster — Doc 8 §6.2 domain service.

Looks up the currently registered model for ``SOLAR_GENERATION``, builds its
features from telemetry, and produces a ``Forecast`` through the shared
``ForecastingService`` — the model itself is swappable (baseline today,
``XGBoostForecaster`` once registered) without this class changing at all.
"""

from __future__ import annotations

from datetime import timedelta

from solarops.forecast.application.feature_engineering import build_features
from solarops.forecast.application.forecasting_service import ForecastingService
from solarops.forecast.domain.events import ForecastGenerated
from solarops.forecast.domain.exceptions import NoRegisteredModel
from solarops.forecast.domain.forecast import Forecast
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.ports import HistoricalDataSource, ModelRegistry
from solarops.forecast.infrastructure.config import ForecastConfig
from solarops.telemetry.domain.energy_state import EnergyState

__all__ = ["SolarGenerationForecaster"]


class SolarGenerationForecaster:
    def __init__(
        self,
        service: ForecastingService,
        registry: ModelRegistry,
        history_source: HistoricalDataSource,
        config: ForecastConfig,
    ) -> None:
        self._service = service
        self._registry = registry
        self._history_source = history_source
        self._config = config

    def forecast(self, current: EnergyState) -> tuple[Forecast, ForecastGenerated]:
        model = self._registry.get_current(ForecastKind.SOLAR_GENERATION)
        if model is None:
            raise NoRegisteredModel(ForecastKind.SOLAR_GENERATION)

        history = self._history_source.get_history(
            current.site_id,
            as_of=current.timestamp,
            lookback=timedelta(hours=self._config.lookback_hours),
        )
        features = build_features(ForecastKind.SOLAR_GENERATION, current, history, self._config)
        return self._service.generate(
            current.site_id,
            model,
            features,
            self._config.max_horizon_minutes,
            self._config.resolution_minutes,
        )
