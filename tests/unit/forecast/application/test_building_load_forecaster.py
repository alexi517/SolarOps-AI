from datetime import UTC, datetime

import pytest

from solarops.forecast.application.building_load_forecaster import BuildingLoadForecaster
from solarops.forecast.application.forecasting_service import ForecastingService
from solarops.forecast.domain.exceptions import NoRegisteredModel
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.infrastructure.config import ForecastConfig
from solarops.forecast.infrastructure.historical_data_source import InMemoryHistoricalDataSource
from solarops.forecast.infrastructure.in_memory_forecast_repository import (
    InMemoryForecastRepository,
)
from solarops.forecast.infrastructure.model_registry import InMemoryModelRegistry
from solarops.forecast.infrastructure.models.load_baseline import LoadBaseline
from solarops.shared_kernel import FixedClock, Power, SiteId
from solarops.telemetry.domain.energy_state import EnergyState

from ...telemetry.domain.test_telemetry import make_telemetry

SITE_ID = SiteId("SITE-1")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_state(**overrides) -> EnergyState:
    telemetry = make_telemetry(site_id=SITE_ID, **overrides)
    return EnergyState.from_telemetry(telemetry, any_asset_offline=False)


def make_forecaster(registry: InMemoryModelRegistry | None = None):
    config = ForecastConfig()
    service = ForecastingService(InMemoryForecastRepository(), FixedClock(NOW))
    registry = registry or InMemoryModelRegistry()
    history_source = InMemoryHistoricalDataSource()
    return BuildingLoadForecaster(service, registry, history_source, config), registry


def test_raises_when_no_model_registered():
    forecaster, _ = make_forecaster()
    with pytest.raises(NoRegisteredModel):
        forecaster.forecast(make_state())


def test_produces_forecast_through_registered_model():
    registry = InMemoryModelRegistry()
    registry.register(LoadBaseline(), metrics={})
    forecaster, _ = make_forecaster(registry)

    current = make_state(timestamp=NOW, building_load=Power(30.0))
    forecast, event = forecaster.forecast(current)

    assert forecast.kind is ForecastKind.BUILDING_LOAD
    assert forecast.metadata.model_name == "load-baseline"
    assert len(forecast.points) > 1
    assert event.kind is ForecastKind.BUILDING_LOAD
