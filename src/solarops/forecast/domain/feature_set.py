"""FeatureSet / TrainingExample — the model-agnostic input to a ``ForecastModel``.

Not named as a file in the Phase 6a brief's file list, but required by its own
``ports.py`` bullet (§3: ``predict(features, horizon)``, ``fit(training_set)``)
— filled in here rather than guessed inline in ``ports.py``, so both the
Protocols and ``feature_engineering.py`` import one shared definition.

``FeatureSet`` is deliberately a named ``dict[str, float]`` rather than a fixed
set of fields: a baseline model reads two or three keys, ``XGBoostForecaster``
reads all of them, and adding a feature never changes either model's
signature — only ``ForecastConfig``'s per-kind feature list and
``feature_engineering.py``'s construction of it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from solarops.forecast.domain.forecast_kind import ForecastKind

__all__ = ["FeatureSet", "TrainingExample"]


@dataclass(frozen=True, slots=True)
class FeatureSet:
    """Named features as-of one point in time, for one forecast kind."""

    kind: ForecastKind
    as_of: datetime
    values: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TrainingExample:
    """One supervised-learning row: features observed, and what actually happened next."""

    features: FeatureSet
    horizon_minutes: int
    target: float
