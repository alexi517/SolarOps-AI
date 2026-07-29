"""XGBoostForecaster — first ML model, proves the ``ForecastModel``/``TrainableModel``
interface (brief §4).

Parameterised by ``ForecastKind`` so one implementation serves Solar and Load
(§5 keeps Battery SOC on the deterministic baseline in v1 — see
``battery_soc_baseline.py``). ``horizon_minutes`` is folded in as a training
feature so one fitted model can answer any horizon within the configured
range, rather than needing one model per named horizon.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import xgboost as xgb

from solarops.forecast.domain.feature_set import FeatureSet, TrainingExample
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.forecast_point import ForecastPoint
from solarops.forecast.domain.ports import FitResult
from solarops.shared_kernel import Power, StateOfCharge

__all__ = ["XGBoostForecaster"]


def _clamp(kind: ForecastKind, value: float) -> float:
    if kind is ForecastKind.BATTERY_SOC:
        return min(100.0, max(0.0, value))
    return value


class XGBoostForecaster:
    """Gradient-boosted regression, one fitted model per ``ForecastKind``."""

    def __init__(
        self,
        kind: ForecastKind,
        feature_names: tuple[str, ...],
        resolution_minutes: int = 15,
        version: str = "v1",
        **xgb_params: object,
    ) -> None:
        self.kind = kind
        self.name = f"xgboost-{kind.value.lower()}"
        self.version = version
        self.resolution_minutes = resolution_minutes
        self._feature_names = feature_names
        self._xgb_params = xgb_params or {"n_estimators": 50, "max_depth": 3}
        self._model: xgb.XGBRegressor | None = None

    @property
    def is_fitted(self) -> bool:
        return self._model is not None

    def fit(self, training_set: list[TrainingExample]) -> FitResult:
        if not training_set:
            raise ValueError(f"{self.name}: cannot fit on an empty training set")

        rows = [self._row(example.features, example.horizon_minutes) for example in training_set]
        targets = [example.target for example in training_set]

        model = xgb.XGBRegressor(**self._xgb_params)
        model.fit(np.array(rows), np.array(targets))
        self._model = model
        return FitResult(trained_on=len(training_set), trained_at=datetime.now(UTC))

    def predict(self, features: FeatureSet, horizon_minutes: int) -> list[ForecastPoint]:
        if self._model is None:
            raise RuntimeError(f"{self.name} has not been fitted yet")

        elapsed_steps = list(range(0, horizon_minutes + 1, self.resolution_minutes))
        rows = np.array([self._row(features, elapsed) for elapsed in elapsed_steps])
        predictions = self._model.predict(rows)

        value_cls = StateOfCharge if self.kind is ForecastKind.BATTERY_SOC else Power
        points = []
        for elapsed, prediction in zip(elapsed_steps, predictions, strict=True):
            timestamp = features.as_of + timedelta(minutes=elapsed)
            value = value_cls(round(_clamp(self.kind, float(prediction)), 3))
            points.append(ForecastPoint(timestamp=timestamp, value=value))
        return points

    def _row(self, features: FeatureSet, horizon_minutes: int) -> list[float]:
        return [features.values.get(name, 0.0) for name in self._feature_names] + [
            float(horizon_minutes)
        ]
