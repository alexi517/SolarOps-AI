from datetime import UTC, datetime

import pytest

from solarops.forecast.domain.feature_set import FeatureSet, TrainingExample
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.infrastructure.models.xgboost_forecaster import XGBoostForecaster

NOW = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
FEATURE_NAMES = ("x1", "x2")


def make_features(kind: ForecastKind = ForecastKind.SOLAR_GENERATION, **values) -> FeatureSet:
    defaults = {"x1": 1.0, "x2": 1.0}
    defaults.update(values)
    return FeatureSet(kind=kind, as_of=NOW, values=defaults)


def make_training_set(n: int = 30) -> list[TrainingExample]:
    examples = []
    for i in range(n):
        x1 = float(i)
        target = 2.0 * x1 + 5.0
        features = make_features(x1=x1)
        examples.append(TrainingExample(features=features, horizon_minutes=15, target=target))
    return examples


def test_predict_before_fit_raises():
    model = XGBoostForecaster(ForecastKind.SOLAR_GENERATION, FEATURE_NAMES)
    with pytest.raises(RuntimeError, match="not been fitted"):
        model.predict(make_features(), horizon_minutes=15)


def test_fit_on_empty_set_raises():
    model = XGBoostForecaster(ForecastKind.SOLAR_GENERATION, FEATURE_NAMES)
    with pytest.raises(ValueError, match="empty"):
        model.fit([])


def test_fit_then_predict_learns_the_relationship():
    model = XGBoostForecaster(
        ForecastKind.SOLAR_GENERATION, FEATURE_NAMES, n_estimators=50, max_depth=3
    )
    result = model.fit(make_training_set())
    assert result.trained_on == 30
    assert model.is_fitted is True

    points = model.predict(make_features(x1=10.0), horizon_minutes=15)
    assert points[-1].value.value == pytest.approx(25.0, abs=3.0)


def test_battery_soc_predictions_are_clamped():
    model = XGBoostForecaster(ForecastKind.BATTERY_SOC, FEATURE_NAMES, n_estimators=10)
    examples = [
        TrainingExample(
            features=make_features(kind=ForecastKind.BATTERY_SOC),
            horizon_minutes=15,
            target=500.0,  # deliberately out-of-range target to try to push predictions past 100
        )
        for _ in range(5)
    ]
    model.fit(examples)
    points = model.predict(make_features(kind=ForecastKind.BATTERY_SOC), horizon_minutes=15)
    assert all(0.0 <= p.value.value <= 100.0 for p in points)


def test_predict_series_matches_resolution():
    model = XGBoostForecaster(ForecastKind.SOLAR_GENERATION, FEATURE_NAMES, resolution_minutes=15)
    model.fit(make_training_set())
    points = model.predict(make_features(), horizon_minutes=60)
    assert len(points) == 5


def test_carries_identity():
    model = XGBoostForecaster(ForecastKind.BUILDING_LOAD, FEATURE_NAMES)
    assert model.name == "xgboost-building_load"
    assert model.kind is ForecastKind.BUILDING_LOAD
