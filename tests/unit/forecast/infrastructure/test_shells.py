from datetime import UTC, datetime

import pytest

from solarops.forecast.domain.feature_set import FeatureSet
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.infrastructure.models.shells import (
    LightGBMForecaster,
    LSTMForecaster,
    ProphetForecaster,
)

NOW = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize("shell_cls", [ProphetForecaster, LightGBMForecaster, LSTMForecaster])
def test_shell_carries_kind_and_raises_on_predict(shell_cls):
    model = shell_cls(ForecastKind.SOLAR_GENERATION)
    assert model.kind is ForecastKind.SOLAR_GENERATION
    features = FeatureSet(kind=ForecastKind.SOLAR_GENERATION, as_of=NOW, values={})
    with pytest.raises(NotImplementedError):
        model.predict(features, horizon_minutes=15)


@pytest.mark.parametrize("shell_cls", [ProphetForecaster, LightGBMForecaster, LSTMForecaster])
def test_shell_raises_on_fit(shell_cls):
    model = shell_cls(ForecastKind.BUILDING_LOAD)
    with pytest.raises(NotImplementedError):
        model.fit([])
