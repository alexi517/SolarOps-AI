from datetime import UTC, datetime, timedelta

import pytest

from solarops.forecast.application.battery_soc_forecaster import BatterySocForecaster
from solarops.forecast.application.forecasting_service import ForecastingService
from solarops.forecast.domain.exceptions import NoRegisteredModel
from solarops.forecast.domain.forecast import Forecast
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.forecast_metadata import ForecastMetadata
from solarops.forecast.domain.forecast_point import ForecastPoint
from solarops.forecast.infrastructure.config import ForecastConfig
from solarops.forecast.infrastructure.in_memory_forecast_repository import (
    InMemoryForecastRepository,
)
from solarops.forecast.infrastructure.model_registry import InMemoryModelRegistry
from solarops.forecast.infrastructure.models.battery_soc_baseline import BatterySocBaseline
from solarops.shared_kernel import FixedClock, ForecastId, Power, SiteId, StateOfCharge
from solarops.telemetry.domain.energy_state import EnergyState

from ...telemetry.domain.test_telemetry import make_telemetry

SITE_ID = SiteId("SITE-1")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_state(**overrides) -> EnergyState:
    telemetry = make_telemetry(site_id=SITE_ID, **overrides)
    return EnergyState.from_telemetry(telemetry, any_asset_offline=False)


def make_side_forecast(kind: ForecastKind, power_kw: float) -> Forecast:
    points = [
        ForecastPoint(timestamp=NOW + timedelta(minutes=m), value=Power(power_kw))
        for m in (0, 15, 30)
    ]
    return Forecast(
        forecast_id=ForecastId.generate(),
        site_id=SITE_ID,
        kind=kind,
        horizon_minutes=30,
        points=tuple(points),
        metadata=ForecastMetadata(
            model_name="stub", model_version="v1", generated_at=NOW,
            horizon_minutes=30, resolution_minutes=15,
        ),
    )


def make_forecaster(registry: InMemoryModelRegistry | None = None):
    config = ForecastConfig()
    service = ForecastingService(InMemoryForecastRepository(), FixedClock(NOW))
    registry = registry or InMemoryModelRegistry()
    return BatterySocForecaster(service, registry, config), registry


def test_raises_when_no_model_registered():
    forecaster, _ = make_forecaster()
    solar = make_side_forecast(ForecastKind.SOLAR_GENERATION, 40.0)
    load = make_side_forecast(ForecastKind.BUILDING_LOAD, 20.0)
    with pytest.raises(NoRegisteredModel):
        forecaster.forecast(make_state(), solar, load)


def test_produces_soc_forecast_from_solar_and_load_forecasts():
    registry = InMemoryModelRegistry()
    baseline = BatterySocBaseline(capacity_kwh=200.0, round_trip_efficiency=0.92)
    registry.register(baseline, metrics={})
    forecaster, _ = make_forecaster(registry)

    solar = make_side_forecast(ForecastKind.SOLAR_GENERATION, 40.0)
    load = make_side_forecast(ForecastKind.BUILDING_LOAD, 20.0)
    current = make_state(timestamp=NOW, battery_soc=StateOfCharge(50.0))

    forecast, event = forecaster.forecast(current, solar, load)

    assert forecast.kind is ForecastKind.BATTERY_SOC
    assert all(0.0 <= p.value.value <= 100.0 for p in forecast.points)
    # net power is positive (charging) -> SOC should trend upward
    assert forecast.points[-1].value.value >= forecast.points[0].value.value
    assert event.kind is ForecastKind.BATTERY_SOC
