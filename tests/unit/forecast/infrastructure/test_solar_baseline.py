from datetime import UTC, datetime

from solarops.forecast.domain.feature_set import FeatureSet
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.infrastructure.models.solar_baseline import SolarBaseline

NOON = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
MIDNIGHT = datetime(2026, 6, 15, 0, 0, tzinfo=UTC)


def make_features(**values) -> FeatureSet:
    return FeatureSet(kind=ForecastKind.SOLAR_GENERATION, as_of=NOON, values=values)


def test_produces_series_at_configured_resolution_out_to_horizon():
    model = SolarBaseline(capacity_kw=100.0, resolution_minutes=15)
    points = model.predict(make_features(cloud_cover_pct=0.0), horizon_minutes=60)
    assert [p.timestamp.minute for p in points] == [0, 15, 30, 45, 0]
    assert len(points) == 5


def test_zero_at_night():
    model = SolarBaseline(capacity_kw=100.0)
    features = FeatureSet(
        kind=ForecastKind.SOLAR_GENERATION, as_of=MIDNIGHT, values={"cloud_cover_pct": 0.0}
    )
    points = model.predict(features, horizon_minutes=0)
    assert points[0].value.value == 0.0


def test_positive_at_midday_clear_sky():
    model = SolarBaseline(capacity_kw=100.0)
    points = model.predict(make_features(cloud_cover_pct=0.0), horizon_minutes=0)
    assert points[0].value.value > 0.0


def test_cloud_cover_reduces_output():
    model = SolarBaseline(capacity_kw=100.0)
    clear = model.predict(make_features(cloud_cover_pct=0.0), horizon_minutes=0)[0].value.value
    cloudy = model.predict(make_features(cloud_cover_pct=100.0), horizon_minutes=0)[0].value.value
    assert cloudy < clear


def test_carries_identity():
    model = SolarBaseline()
    assert model.name == "solar-baseline"
    assert model.kind is ForecastKind.SOLAR_GENERATION
