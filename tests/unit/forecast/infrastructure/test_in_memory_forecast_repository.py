from datetime import UTC, datetime

from solarops.forecast.domain.forecast import Forecast
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.forecast_metadata import ForecastMetadata
from solarops.forecast.domain.forecast_point import ForecastPoint
from solarops.forecast.infrastructure.in_memory_forecast_repository import (
    InMemoryForecastRepository,
)
from solarops.shared_kernel import ForecastId, Power, SiteId

SITE_ID = SiteId("SITE-1")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_forecast(kind=ForecastKind.SOLAR_GENERATION, site_id=SITE_ID) -> Forecast:
    return Forecast(
        forecast_id=ForecastId.generate(),
        site_id=site_id,
        kind=kind,
        horizon_minutes=60,
        points=(ForecastPoint(timestamp=NOW, value=Power(10.0)),),
        metadata=ForecastMetadata(
            model_name="m", model_version="v1", generated_at=NOW,
            horizon_minutes=60, resolution_minutes=15,
        ),
    )


def test_get_latest_is_none_before_save():
    repository = InMemoryForecastRepository()
    assert repository.get_latest(SITE_ID, ForecastKind.SOLAR_GENERATION) is None


def test_save_then_get_latest_round_trips():
    repository = InMemoryForecastRepository()
    forecast = make_forecast()
    repository.save(forecast)
    assert repository.get_latest(SITE_ID, ForecastKind.SOLAR_GENERATION) == forecast


def test_save_replaces_the_previous_forecast_for_the_same_site_and_kind():
    repository = InMemoryForecastRepository()
    repository.save(make_forecast())
    second = make_forecast()
    repository.save(second)
    assert repository.get_latest(SITE_ID, ForecastKind.SOLAR_GENERATION) == second


def test_kept_independent_per_kind():
    repository = InMemoryForecastRepository()
    repository.save(make_forecast(kind=ForecastKind.SOLAR_GENERATION))
    assert repository.get_latest(SITE_ID, ForecastKind.BUILDING_LOAD) is None
