"""Class shells against the ``ForecastModel``/``TrainableModel`` interface (brief §4).

Not implemented yet — proves the interface accommodates them (name/version/kind
present, correct method signatures) without any of the three actually doing
anything until a later phase implements them.
"""

from __future__ import annotations

from solarops.forecast.domain.feature_set import FeatureSet, TrainingExample
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.forecast_point import ForecastPoint
from solarops.forecast.domain.ports import FitResult

__all__ = ["ProphetForecaster", "LightGBMForecaster", "LSTMForecaster"]


class _UnimplementedModelShell:
    version = "unimplemented"

    def __init__(self, kind: ForecastKind) -> None:
        self.kind = kind

    def predict(self, features: FeatureSet, horizon_minutes: int) -> list[ForecastPoint]:
        raise NotImplementedError(f"{self.name} is not implemented yet (Phase 6a brief §4)")

    def fit(self, training_set: list[TrainingExample]) -> FitResult:
        raise NotImplementedError(f"{self.name} is not implemented yet (Phase 6a brief §4)")


class ProphetForecaster(_UnimplementedModelShell):
    name = "prophet"


class LightGBMForecaster(_UnimplementedModelShell):
    name = "lightgbm"


class LSTMForecaster(_UnimplementedModelShell):
    name = "lstm"
