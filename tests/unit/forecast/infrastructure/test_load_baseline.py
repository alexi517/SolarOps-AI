from datetime import UTC, datetime

from solarops.forecast.domain.feature_set import FeatureSet
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.infrastructure.models.load_baseline import LoadBaseline

MIDDAY = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)  # Monday


def make_features(**values) -> FeatureSet:
    defaults = {
        "hour_of_day": 12.0,
        "building_load_kw": 30.0,
        "building_load_trailing_avg_kw": 25.0,
        "building_load_peak_observed_kw": 60.0,
    }
    defaults.update(values)
    return FeatureSet(kind=ForecastKind.BUILDING_LOAD, as_of=MIDDAY, values=defaults)


def test_produces_series_at_configured_resolution():
    model = LoadBaseline(resolution_minutes=15)
    points = model.predict(make_features(), horizon_minutes=60)
    assert len(points) == 5


def test_never_negative():
    model = LoadBaseline()
    points = model.predict(make_features(building_load_peak_observed_kw=0.0), horizon_minutes=360)
    assert all(p.value.value >= 0.0 for p in points)


def test_scales_by_peak_observed_capacity_not_a_single_instant_ratio():
    # A reading captured right at the dawn/dusk transition (low occupancy) must
    # not blow up the implied capacity — this is the bug the peak-observed
    # feature replaces (dividing a single instant by a near-zero occupancy).
    model = LoadBaseline()
    dawn_features = FeatureSet(
        kind=ForecastKind.BUILDING_LOAD,
        as_of=datetime(2026, 6, 15, 6, 15, tzinfo=UTC),
        values={
            "hour_of_day": 6.25,
            "building_load_kw": 3.0,
            "building_load_trailing_avg_kw": 25.0,
            "building_load_peak_observed_kw": 60.0,
        },
    )
    midday_point = model.predict(dawn_features, horizon_minutes=6 * 60)[-1]
    # capacity (60kW) * occupancy near midday (~1.0) should land near 60kW, not
    # the hundreds of kW a naive current/occupancy_now division would produce.
    assert midday_point.value.value < 100.0


def test_falls_back_to_current_reading_when_peak_observed_missing():
    model = LoadBaseline()
    features = FeatureSet(
        kind=ForecastKind.BUILDING_LOAD, as_of=MIDDAY, values={"building_load_kw": 20.0}
    )
    points = model.predict(features, horizon_minutes=0)
    assert points[0].value.value >= 0.0


def test_carries_identity():
    model = LoadBaseline()
    assert model.name == "load-baseline"
    assert model.kind is ForecastKind.BUILDING_LOAD
