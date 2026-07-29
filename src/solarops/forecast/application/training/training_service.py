"""TrainingService — fit -> evaluate (brief §6 gate) -> register only on pass (brief §3).

The gate is enforced in exactly one place: ``evaluate_and_register`` always
runs the evaluator before ``ModelRegistry.register`` is ever called, and only
calls it when ``EvaluationReport.passed`` is true. Baselines (no ``fit``) skip
straight to evaluation; ``TrainableModel``s go through ``train_and_evaluate``,
which fits first.
"""

from __future__ import annotations

from dataclasses import dataclass

from solarops.forecast.application.evaluation.forecast_evaluator import (
    EvaluationReport,
    ForecastEvaluator,
)
from solarops.forecast.domain.feature_set import TrainingExample
from solarops.forecast.domain.ports import ForecastModel, ModelRegistry, TrainableModel

__all__ = ["TrainingOutcome", "TrainingService"]


@dataclass(frozen=True, slots=True)
class TrainingOutcome:
    report: EvaluationReport
    registered: bool


class TrainingService:
    def __init__(self, evaluator: ForecastEvaluator, registry: ModelRegistry) -> None:
        self._evaluator = evaluator
        self._registry = registry

    def evaluate_and_register(self, model: ForecastModel) -> TrainingOutcome:
        """Run the gate against the currently released model's metrics; register only on pass."""
        previous_metrics = self._registry.get_current_metrics(model.kind)
        report = self._evaluator.evaluate(model, previous_metrics)

        if report.passed:
            self._registry.register(model, report.metrics_summary)
            return TrainingOutcome(report=report, registered=True)
        return TrainingOutcome(report=report, registered=False)

    def train_and_evaluate(
        self, model: TrainableModel, training_set: list[TrainingExample]
    ) -> TrainingOutcome:
        model.fit(training_set)
        return self.evaluate_and_register(model)

    def retrain(
        self, model: TrainableModel, training_set: list[TrainingExample]
    ) -> TrainingOutcome:
        """Re-fit an already-registered model on fresh data and re-run the gate.

        Drift-triggered retraining (brief §3: "drift = later seam") would call
        this once a drift signal exists; today it is a callable entry point
        with no scheduler behind it, identical in behaviour to initial training.
        """
        return self.train_and_evaluate(model, training_set)
