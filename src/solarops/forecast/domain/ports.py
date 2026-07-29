"""Ports the Forecast context depends on.

Defined in domain, implemented in infrastructure (Doc 8 §9.1). ``ForecastModel``
and ``TrainableModel`` are the model-swappable interface that is the whole
architectural point of Phase 6a (brief §0): baselines implement ``ForecastModel``
only; ``XGBoostForecaster`` implements both.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol, runtime_checkable

from solarops.forecast.domain.feature_set import FeatureSet, TrainingExample
from solarops.forecast.domain.forecast import Forecast
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.forecast_point import ForecastPoint
from solarops.shared_kernel import SiteId
from solarops.telemetry.domain.energy_state import EnergyState

__all__ = [
    "FitResult",
    "ForecastModel",
    "TrainableModel",
    "ForecastRepository",
    "HistoricalDataSource",
    "ModelRegistry",
    "BenchmarkRun",
    "BenchmarkScenarioSource",
]


@dataclass(frozen=True, slots=True)
class FitResult:
    """Outcome of ``TrainableModel.fit`` — how much data trained the model."""

    trained_on: int
    trained_at: datetime


@runtime_checkable
class ForecastModel(Protocol):
    """The one interface every predictor implements — deterministic or ML.

    Carries its own identity so a ``Forecast``'s metadata can always say
    exactly which model produced it.
    """

    name: str
    version: str
    kind: ForecastKind

    def predict(self, features: FeatureSet, horizon_minutes: int) -> list[ForecastPoint]: ...


@runtime_checkable
class TrainableModel(ForecastModel, Protocol):
    """A ``ForecastModel`` that can also be fit on historical examples."""

    def fit(self, training_set: list[TrainingExample]) -> FitResult: ...


class ForecastRepository(Protocol):
    def save(self, forecast: Forecast) -> None: ...

    def get_latest(self, site_id: SiteId, kind: ForecastKind) -> Forecast | None: ...


class HistoricalDataSource(Protocol):
    """Raw history a forecaster can turn into features/training examples.

    Implemented at the platform composition root by running the Digital Twin
    (Phase 6a brief §7) — Forecast itself never imports Simulation.
    """

    def get_history(
        self, site_id: SiteId, *, as_of: datetime, lookback: timedelta
    ) -> list[EnergyState]: ...


class ModelRegistry(Protocol):
    """Tracks the currently-released model per kind, and candidate registrations.

    ``register`` is only ever called after a model has passed the evaluation
    gate (Phase 6a brief §6) — the registry itself does not enforce that; the
    training pipeline does, so the gate stays a single, testable decision point.
    """

    def get_current(self, kind: ForecastKind) -> ForecastModel | None: ...

    def register(self, model: ForecastModel, metrics: dict[str, float]) -> None: ...

    def get_current_metrics(self, kind: ForecastKind) -> dict[str, float] | None: ...


@dataclass(frozen=True, slots=True)
class BenchmarkRun:
    """One benchmark scenario's ground truth: features observed vs. what happened next.

    ``is_primary`` distinguishes the three forecast-accuracy scenarios (Clear
    Day, Cloud Front, Evening Peak) from the three robustness scenarios (Grid
    Outage, Battery Overheating, Sensor Failure) per the brief §6 note — only
    primary scenarios' metrics count toward the release gate; robustness
    scenarios only need to run without the pipeline breaking.
    """

    scenario_name: str
    is_primary: bool
    examples: dict[ForecastKind, list[TrainingExample]]


class BenchmarkScenarioSource(Protocol):
    """Runs the six Document 6 §9 benchmark scenarios through the Digital Twin.

    Implemented at the platform composition root — it spans Simulation and
    Forecast, which is orchestration, not something either context may import
    directly (Phase 6a brief §8).
    """

    def scenario_names(self) -> list[str]: ...

    def run(self, scenario_name: str) -> BenchmarkRun: ...
