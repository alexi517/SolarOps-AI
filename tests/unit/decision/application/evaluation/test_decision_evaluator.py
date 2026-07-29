from datetime import UTC, datetime

from solarops.decision.application.evaluation.decision_evaluator import (
    EXPECTED_DECISIONS,
    DecisionEvaluator,
)
from solarops.decision.domain.decision_context import DecisionContext
from solarops.decision.domain.operating_constraints import OperatingConstraints
from solarops.decision.domain.ranked_recommendations import RankedRecommendations
from solarops.decision.domain.recommendation import Recommendation
from solarops.shared_kernel import (
    ActionType,
    Power,
    RecommendationId,
    SiteId,
    StateOfCharge,
    Temperature,
)
from solarops.telemetry.domain.energy_state import EnergyState

from ....telemetry.domain.test_telemetry import make_telemetry

SITE_ID = SiteId("SITE-1")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_context() -> DecisionContext:
    state = EnergyState.from_telemetry(
        make_telemetry(site_id=SITE_ID, timestamp=NOW), any_asset_offline=False
    )
    constraints = OperatingConstraints(
        max_battery_soc=StateOfCharge(95.0),
        min_battery_soc=StateOfCharge(10.0),
        battery_max_temp=Temperature(45.0),
        battery_max_charge_power=Power(50.0),
        battery_max_discharge_power=Power(50.0),
        maintenance_mode=False,
        max_shed_fraction=0.3,
    )
    return DecisionContext(energy_state=state, operating_constraints=constraints)


class _FakeScenarioSource:
    def __init__(self, contexts: dict[str, DecisionContext]) -> None:
        self._contexts = contexts

    def scenario_names(self) -> list[str]:
        return list(self._contexts.keys())

    def context_for(self, scenario_name: str) -> DecisionContext:
        return self._contexts[scenario_name]


class _FakeEngine:
    name = "fake-engine"
    version = "v1"

    def __init__(self, action: ActionType, confidence: float = 0.8) -> None:
        self._action = action
        self._confidence = confidence

    def recommend(self, context: DecisionContext) -> RankedRecommendations:
        recommendation = Recommendation(
            recommendation_id=RecommendationId.generate(),
            site_id=SITE_ID,
            action=self._action,
            confidence=self._confidence,
            expected_benefit="x",
            reason="x",
            generated_at=NOW,
        )
        return RankedRecommendations(recommendations=(recommendation,))


def test_default_expected_decisions_are_all_unmarked_todo():
    assert all(value is None for value in EXPECTED_DECISIONS.values())


def test_scenario_with_no_expected_decision_is_reported_unevaluated():
    source = _FakeScenarioSource({"Clear Day": make_context()})
    evaluator = DecisionEvaluator(source)  # uses EXPECTED_DECISIONS -> None

    report = evaluator.evaluate(_FakeEngine(ActionType.HOLD_BATTERY))

    assert report.scenario_results[0].evaluated is False
    assert report.scenario_results[0].accuracy is None
    assert report.unevaluated_scenarios == ("Clear Day",)
    assert report.mean_decision_accuracy is None


def test_scenario_with_expected_decision_is_evaluated():
    source = _FakeScenarioSource({"S1": make_context()})
    evaluator = DecisionEvaluator(source, expected_decisions={"S1": ActionType.HOLD_BATTERY})

    report = evaluator.evaluate(_FakeEngine(ActionType.HOLD_BATTERY))

    assert report.scenario_results[0].evaluated is True
    assert report.scenario_results[0].accuracy == 1.0
    assert report.mean_decision_accuracy == 1.0


def test_wrong_prediction_scores_zero_accuracy():
    source = _FakeScenarioSource({"S1": make_context()})
    evaluator = DecisionEvaluator(source, expected_decisions={"S1": ActionType.CHARGE_BATTERY})

    report = evaluator.evaluate(_FakeEngine(ActionType.HOLD_BATTERY))

    assert report.scenario_results[0].accuracy == 0.0
    assert report.mean_decision_accuracy == 0.0


def test_confidence_calibration_error_reflects_overconfidence_on_a_miss():
    source = _FakeScenarioSource({"S1": make_context()})
    evaluator = DecisionEvaluator(source, expected_decisions={"S1": ActionType.CHARGE_BATTERY})

    report = evaluator.evaluate(_FakeEngine(ActionType.HOLD_BATTERY, confidence=1.0))

    assert report.confidence_calibration_error == 1.0
