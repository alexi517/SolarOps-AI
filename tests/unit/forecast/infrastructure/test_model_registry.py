from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.infrastructure.model_registry import InMemoryModelRegistry
from solarops.forecast.infrastructure.models.solar_baseline import SolarBaseline


def test_get_current_is_none_before_registration():
    registry = InMemoryModelRegistry()
    assert registry.get_current(ForecastKind.SOLAR_GENERATION) is None
    assert registry.get_current_metrics(ForecastKind.SOLAR_GENERATION) is None


def test_register_then_get_current_returns_the_model():
    registry = InMemoryModelRegistry()
    model = SolarBaseline()
    registry.register(model, {"solar_mae_pct": 3.0})

    assert registry.get_current(ForecastKind.SOLAR_GENERATION) is model
    assert registry.get_current_metrics(ForecastKind.SOLAR_GENERATION) == {"solar_mae_pct": 3.0}


def test_register_replaces_the_previous_model_for_the_same_kind():
    registry = InMemoryModelRegistry()
    first = SolarBaseline(capacity_kw=50.0)
    second = SolarBaseline(capacity_kw=100.0)
    registry.register(first, {})
    registry.register(second, {})

    assert registry.get_current(ForecastKind.SOLAR_GENERATION) is second


def test_registries_are_keyed_independently_per_kind():
    registry = InMemoryModelRegistry()
    registry.register(SolarBaseline(), {"solar_mae_pct": 1.0})
    assert registry.get_current(ForecastKind.BUILDING_LOAD) is None
