from datetime import UTC, datetime

from solarops.forecast.application.forecasting_service import ForecastingService
from solarops.forecast.domain.feature_set import FeatureSet
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.forecast_point import ForecastPoint
from solarops.forecast.infrastructure.in_memory_forecast_repository import (
    InMemoryForecastRepository,
)
from solarops.shared_kernel import FixedClock, Power, SiteId

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)
SITE_ID = SiteId("SITE-1")


class _StubModel:
    name = "stub-model"
    version = "v1"
    kind = ForecastKind.SOLAR_GENERATION

    def predict(self, features: FeatureSet, horizon_minutes: int) -> list[ForecastPoint]:
        return [ForecastPoint(timestamp=features.as_of, value=Power(10.0))]


def test_generate_persists_and_returns_forecast_with_model_provenance():
    repository = InMemoryForecastRepository()
    service = ForecastingService(repository, FixedClock(NOW))
    features = FeatureSet(kind=ForecastKind.SOLAR_GENERATION, as_of=NOW, values={})

    forecast, event = service.generate(SITE_ID, _StubModel(), features, 360, 15)

    assert forecast.metadata.model_name == "stub-model"
    assert forecast.metadata.model_version == "v1"
    assert forecast.kind is ForecastKind.SOLAR_GENERATION
    assert repository.get_latest(SITE_ID, ForecastKind.SOLAR_GENERATION) == forecast


def test_generate_emits_forecast_generated_event():
    repository = InMemoryForecastRepository()
    service = ForecastingService(repository, FixedClock(NOW))
    features = FeatureSet(kind=ForecastKind.SOLAR_GENERATION, as_of=NOW, values={})

    forecast, event = service.generate(SITE_ID, _StubModel(), features, 360, 15)

    assert event.event_type == "ForecastGenerated"
    assert event.aggregate_id == str(forecast.forecast_id)
    assert event.model_name == "stub-model"
