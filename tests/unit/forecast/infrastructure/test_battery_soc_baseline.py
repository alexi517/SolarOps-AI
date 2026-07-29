from datetime import UTC, datetime

from solarops.forecast.domain.feature_set import FeatureSet
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.infrastructure.models.battery_soc_baseline import BatterySocBaseline

NOW = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)


def make_model(**overrides) -> BatterySocBaseline:
    defaults = dict(capacity_kwh=200.0, round_trip_efficiency=0.92, resolution_minutes=60)
    defaults.update(overrides)
    return BatterySocBaseline(**defaults)


def make_features(**values) -> FeatureSet:
    return FeatureSet(kind=ForecastKind.BATTERY_SOC, as_of=NOW, values=values)


def test_soc_rises_when_surplus_solar():
    model = make_model()
    features = make_features(
        current_soc_pct=50.0, avg_expected_solar_kw=40.0, avg_expected_load_kw=10.0
    )
    points = model.predict(features, horizon_minutes=60)
    assert points[-1].value.value > points[0].value.value


def test_soc_falls_when_demand_exceeds_generation():
    model = make_model()
    features = make_features(
        current_soc_pct=50.0, avg_expected_solar_kw=5.0, avg_expected_load_kw=30.0
    )
    points = model.predict(features, horizon_minutes=60)
    assert points[-1].value.value < points[0].value.value


def test_soc_clamped_to_valid_range():
    model = make_model(capacity_kwh=10.0)
    features = make_features(
        current_soc_pct=95.0, avg_expected_solar_kw=1000.0, avg_expected_load_kw=0.0
    )
    points = model.predict(features, horizon_minutes=360)
    assert all(0.0 <= p.value.value <= 100.0 for p in points)


def test_carries_identity():
    model = BatterySocBaseline()
    assert model.name == "battery-soc-baseline"
    assert model.kind is ForecastKind.BATTERY_SOC
