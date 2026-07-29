"""DecisionEvaluator — Document 6 §6 decision-quality hooks (brief §7).

Runs an ``OptimisationEngine`` against each Document 6 §9 benchmark scenario
and compares its top recommendation to an expected decision — where Document
6 actually specifies one. It never does: §9 names the six scenarios but never
spells out a numeric "expected AI response" for any of them anywhere in the
document. Per the brief ("leave a TODO(expected-decisions) seam rather than
inventing the expected answer — same discipline as prior phases"), every
scenario here maps to ``None`` and is reported as not-evaluated, never
silently skipped or faked with an invented target.
"""

from __future__ import annotations

from dataclasses import dataclass

from solarops.decision.application.evaluation.metrics import (
    confidence_calibration,
    decision_accuracy,
)
from solarops.decision.domain.ports import BenchmarkContextSource, OptimisationEngine
from solarops.shared_kernel import ActionType

__all__ = [
    "EXPECTED_DECISIONS",
    "ScenarioDecisionResult",
    "DecisionEvaluationReport",
    "DecisionEvaluator",
]

# TODO(expected-decisions): Document 6 §9 names the six benchmark scenarios
# but never specifies what the optimisation engine *should* recommend for any
# of them. Filling these in is a domain-expert decision, not something to
# invent here — see the Phase 6c brief §7.
EXPECTED_DECISIONS: dict[str, ActionType | None] = {
    "Clear Day": None,
    "Cloud Front": None,
    "Evening Peak": None,
    "Grid Outage": None,
    "Battery Overheating": None,
    "Sensor Failure": None,
}


@dataclass(frozen=True, slots=True)
class ScenarioDecisionResult:
    scenario_name: str
    predicted_action: ActionType
    expected_action: ActionType | None
    confidence: float
    accuracy: float | None
    evaluated: bool


@dataclass(frozen=True, slots=True)
class DecisionEvaluationReport:
    engine_name: str
    engine_version: str
    scenario_results: tuple[ScenarioDecisionResult, ...]

    @property
    def evaluated_results(self) -> tuple[ScenarioDecisionResult, ...]:
        return tuple(r for r in self.scenario_results if r.evaluated)

    @property
    def unevaluated_scenarios(self) -> tuple[str, ...]:
        return tuple(r.scenario_name for r in self.scenario_results if not r.evaluated)

    @property
    def mean_decision_accuracy(self) -> float | None:
        evaluated = [r for r in self.evaluated_results if r.accuracy is not None]
        if not evaluated:
            return None
        return sum(r.accuracy for r in evaluated) / len(evaluated)

    @property
    def confidence_calibration_error(self) -> float | None:
        evaluated = [r for r in self.evaluated_results if r.accuracy is not None]
        if not evaluated:
            return None
        return confidence_calibration(
            [r.confidence for r in evaluated], [r.accuracy == 1.0 for r in evaluated]
        )


class DecisionEvaluator:
    def __init__(
        self,
        scenario_source: BenchmarkContextSource,
        expected_decisions: dict[str, ActionType | None] | None = None,
    ) -> None:
        self._scenario_source = scenario_source
        self._expected_decisions = (
            expected_decisions if expected_decisions is not None else EXPECTED_DECISIONS
        )

    def evaluate(self, engine: OptimisationEngine) -> DecisionEvaluationReport:
        results = []
        for scenario_name in self._scenario_source.scenario_names():
            context = self._scenario_source.context_for(scenario_name)
            top = engine.recommend(context).top
            expected = self._expected_decisions.get(scenario_name)
            evaluated = expected is not None
            accuracy = decision_accuracy(top.action, expected) if evaluated else None
            results.append(
                ScenarioDecisionResult(
                    scenario_name=scenario_name,
                    predicted_action=top.action,
                    expected_action=expected,
                    confidence=top.confidence,
                    accuracy=accuracy,
                    evaluated=evaluated,
                )
            )
        return DecisionEvaluationReport(
            engine_name=engine.name,
            engine_version=engine.version,
            scenario_results=tuple(results),
        )
