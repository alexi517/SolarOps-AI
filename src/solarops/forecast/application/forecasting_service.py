"""ForecastingService — shared orchestration for every kind (brief §3).

features -> model.predict -> build Forecast -> persist -> emit ForecastGenerated.
The three per-kind forecasters (``SolarGenerationForecaster``,
``BuildingLoadForecaster``, ``BatterySocForecaster``) each assemble their own
``FeatureSet`` and then call this one shared service — this is where the
"one interface, either model" swap actually happens: ``model`` is whatever
``ModelRegistry.get_current`` returns, baseline or ``XGBoostForecaster`` alike.
"""

from __future__ import annotations

from solarops.forecast.domain.events import ForecastGenerated
from solarops.forecast.domain.feature_set import FeatureSet
from solarops.forecast.domain.forecast import Forecast
from solarops.forecast.domain.forecast_metadata import ForecastMetadata
from solarops.forecast.domain.ports import ForecastModel, ForecastRepository
from solarops.shared_kernel import Clock, ForecastId, SiteId

__all__ = ["ForecastingService"]


class ForecastingService:
    def __init__(self, repository: ForecastRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    def generate(
        self,
        site_id: SiteId,
        model: ForecastModel,
        features: FeatureSet,
        horizon_minutes: int,
        resolution_minutes: int,
    ) -> tuple[Forecast, ForecastGenerated]:
        points = model.predict(features, horizon_minutes)
        metadata = ForecastMetadata(
            model_name=model.name,
            model_version=model.version,
            generated_at=self._clock.now(),
            horizon_minutes=horizon_minutes,
            resolution_minutes=resolution_minutes,
        )
        forecast = Forecast(
            forecast_id=ForecastId.generate(),
            site_id=site_id,
            kind=model.kind,
            horizon_minutes=horizon_minutes,
            points=tuple(points),
            metadata=metadata,
        )
        self._repository.save(forecast)
        event = ForecastGenerated(
            aggregate_id=str(forecast.forecast_id),
            aggregate_type="Forecast",
            kind=forecast.kind,
            model_name=model.name,
            model_version=model.version,
            horizon_minutes=horizon_minutes,
        )
        return forecast, event
