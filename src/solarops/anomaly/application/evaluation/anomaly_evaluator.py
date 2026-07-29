"""AnomalyEvaluator — the Document 6 §5 anomaly metrics and release gate (brief §5).

Runs one detector configuration against the five fault scenarios, tick by
tick, comparing its raw ``detect()`` output to each scenario's ground-truth
labels (a normal-operation prefix, then the injected fault) — the same
"evaluate one candidate independently, before it can join the active set"
choke-point pattern 6a's ``ForecastEvaluator`` uses. A tick counts as a true
positive only if the detector's fired types include the scenario's specific
expected fault type — firing on *something* isn't enough to count as
catching *this* fault.

Gating is per ``AnomalyType``, not per detector as a whole (cleanup pass,
docs/phase6b-cleanup-per-check-gating.md): a detector that covers several
fault types is scored independently on each one, so one weak type (e.g.
Battery Overheating's real thermal-ramp latency) doesn't block registration
of the types it genuinely gets right.
"""

from __future__ import annotations

from dataclasses import dataclass

from solarops.anomaly.application.evaluation.metrics import (
    detection_latency_seconds,
    f1_score,
    false_positive_rate,
    precision,
    recall,
)
from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.domain.ports import AnomalyDetector, FaultScenarioRun, FaultScenarioSource
from solarops.anomaly.infrastructure.config import AnomalyConfig

__all__ = ["ScenarioResult", "EvaluationReport", "AnomalyEvaluator"]


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    scenario_name: str
    expected_type: AnomalyType
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    detection_latency_seconds: float | None
    meets_targets: bool
    regressed: bool = False
    ran_ok: bool = True

    @property
    def passed(self) -> bool:
        """Whether this specific AnomalyType clears the gate: on-target, not a
        regression against the previously registered version for this type, and
        didn't crash."""
        return self.meets_targets and not self.regressed and self.ran_ok


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    detector_name: str
    detector_version: str
    scenario_results: tuple[ScenarioResult, ...]

    @property
    def covered_types(self) -> frozenset[AnomalyType]:
        """The AnomalyTypes this detector configuration is cleared to go live for."""
        return frozenset(r.expected_type for r in self.scenario_results if r.passed)

    @property
    def uncovered_types(self) -> frozenset[AnomalyType]:
        """In-scope types that were evaluated but did not clear the gate."""
        all_types = frozenset(r.expected_type for r in self.scenario_results)
        return all_types - self.covered_types

    @property
    def failed_scenarios(self) -> tuple[ScenarioResult, ...]:
        return tuple(r for r in self.scenario_results if not r.passed)

    @property
    def metrics_by_type(self) -> dict[AnomalyType, dict[str, float]]:
        """Metrics worth persisting per covered type, for future regression checks."""
        return {
            r.expected_type: {"precision": r.precision, "recall": r.recall}
            for r in self.scenario_results
            if r.passed
        }


class AnomalyEvaluator:
    def __init__(self, scenario_source: FaultScenarioSource, config: AnomalyConfig) -> None:
        self._scenario_source = scenario_source
        self._config = config

    def evaluate(
        self,
        detector: AnomalyDetector,
        previous_metrics: dict[AnomalyType, dict[str, float]] | None,
    ) -> EvaluationReport:
        previous_metrics = previous_metrics or {}
        results: list[ScenarioResult] = []
        for scenario_name in self._scenario_source.scenario_names():
            run = self._scenario_source.run(scenario_name)
            if run.expected_type not in detector.supported_types:
                # A detector isn't gated on fault types it never claims to
                # catch — that's what combining several detectors is for
                # (brief §4). Its own in-scope scenarios still cover
                # false-positive behaviour via their normal-operation prefix.
                continue
            try:
                results.append(
                    self._evaluate_scenario(
                        detector, run, previous_metrics.get(run.expected_type)
                    )
                )
            except Exception:  # a detector config must never crash the gate itself
                results.append(
                    ScenarioResult(
                        scenario_name=scenario_name,
                        expected_type=run.expected_type,
                        precision=0.0,
                        recall=0.0,
                        f1=0.0,
                        false_positive_rate=1.0,
                        detection_latency_seconds=None,
                        meets_targets=False,
                        ran_ok=False,
                    )
                )

        return EvaluationReport(
            detector_name=detector.name,
            detector_version=detector.version,
            scenario_results=tuple(results),
        )

    def _evaluate_scenario(
        self,
        detector: AnomalyDetector,
        run: FaultScenarioRun,
        previous_metrics_for_type: dict[str, float] | None,
    ) -> ScenarioResult:
        true_positives = false_positives = false_negatives = true_negatives = 0
        fault_injected_index: int | None = None
        first_true_positive_index: int | None = None
        history = []

        for index, labeled in enumerate(run.readings):
            fired_types = {d.anomaly_type for d in detector.detect(labeled.state, history)}
            history.append(labeled.state)

            if labeled.is_anomalous:
                if fault_injected_index is None:
                    fault_injected_index = index
                if labeled.expected_type in fired_types:
                    true_positives += 1
                    if first_true_positive_index is None:
                        first_true_positive_index = index
                else:
                    false_negatives += 1
            elif fired_types:
                false_positives += 1
            else:
                true_negatives += 1

        precision_value = precision(true_positives, false_positives)
        recall_value = recall(true_positives, false_negatives)
        f1_value = f1_score(precision_value, recall_value)
        fpr_value = false_positive_rate(false_positives, true_negatives)
        latency = (
            detection_latency_seconds(
                fault_injected_index, first_true_positive_index, run.tick_seconds
            )
            if fault_injected_index is not None
            else None
        )

        meets_targets = (
            precision_value >= self._config.precision_target
            and recall_value >= self._config.recall_target
            and (latency is None or latency <= self._config.detection_delay_target_seconds)
        )
        previous_recall = (previous_metrics_for_type or {}).get("recall")
        regressed = previous_recall is not None and recall_value < previous_recall

        return ScenarioResult(
            scenario_name=run.scenario_name,
            expected_type=run.expected_type,
            precision=precision_value,
            recall=recall_value,
            f1=f1_value,
            false_positive_rate=fpr_value,
            detection_latency_seconds=latency,
            meets_targets=meets_targets,
            regressed=regressed,
        )
