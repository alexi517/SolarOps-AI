"""DetectorTrainingService — fit -> evaluate (brief §5 gate) -> register only
what passes (brief §4).

Mirrors ``forecast.application.training.training_service.TrainingService``:
the gate is enforced in exactly one place. Rule/statistical detectors (no
``fit``) skip straight to evaluation; ``TrainableDetector``s (Isolation
Forest) go through ``train_and_evaluate``, which fits first.

Registration is per ``AnomalyType`` (cleanup pass,
docs/phase6b-cleanup-per-check-gating.md): a detector goes active for exactly
the types it clears the gate on. A type that misses its target stays
uncovered — never silently included, never threshold-adjusted to force a
pass.
"""

from __future__ import annotations

from dataclasses import dataclass

from solarops.anomaly.application.evaluation.anomaly_evaluator import (
    AnomalyEvaluator,
    EvaluationReport,
)
from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.domain.ports import AnomalyDetector, DetectorRegistry, TrainableDetector
from solarops.telemetry.domain.energy_state import EnergyState

__all__ = ["TrainingOutcome", "DetectorTrainingService"]


@dataclass(frozen=True, slots=True)
class TrainingOutcome:
    report: EvaluationReport
    covered_types: frozenset[AnomalyType]

    @property
    def registered(self) -> bool:
        return bool(self.covered_types)


class DetectorTrainingService:
    def __init__(self, evaluator: AnomalyEvaluator, registry: DetectorRegistry) -> None:
        self._evaluator = evaluator
        self._registry = registry

    def evaluate_and_register(self, detector: AnomalyDetector) -> TrainingOutcome:
        """Run the gate, per type, against this detector's own previously-stored
        metrics. Registers whichever types pass — nothing else."""
        previous_metrics = self._registry.get_metrics_by_type(detector.name)
        report = self._evaluator.evaluate(detector, previous_metrics)

        covered = report.covered_types
        if covered:
            self._registry.register(detector, covered, report.metrics_by_type)
        return TrainingOutcome(report=report, covered_types=covered)

    def train_and_evaluate(
        self, detector: TrainableDetector, normal_history: list[EnergyState]
    ) -> TrainingOutcome:
        detector.fit(normal_history)
        return self.evaluate_and_register(detector)
