from datetime import UTC, datetime

from solarops.forecast.domain.feature_set import FeatureSet, TrainingExample
from solarops.forecast.domain.forecast_kind import ForecastKind

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def test_feature_set_holds_named_values():
    features = FeatureSet(
        kind=ForecastKind.SOLAR_GENERATION, as_of=NOW, values={"solar_power_kw": 42.0}
    )
    assert features.values["solar_power_kw"] == 42.0
    assert features.kind is ForecastKind.SOLAR_GENERATION


def test_feature_set_values_default_empty():
    features = FeatureSet(kind=ForecastKind.BUILDING_LOAD, as_of=NOW)
    assert features.values == {}


def test_training_example_bundles_features_horizon_and_target():
    features = FeatureSet(kind=ForecastKind.SOLAR_GENERATION, as_of=NOW, values={})
    example = TrainingExample(features=features, horizon_minutes=60, target=12.5)
    assert example.horizon_minutes == 60
    assert example.target == 12.5
