from datetime import UTC, datetime

from solarops.anomaly.application.evaluation.anomaly_evaluator import (
    EvaluationReport,
    ScenarioResult,
)
from solarops.anomaly.application.training.detector_training_service import DetectorTrainingService
from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.domain.ports import FitResult
from solarops.anomaly.infrastructure.detector_registry import InMemoryDetectorRegistry
from solarops.shared_kernel import SiteId
from solarops.telemetry.domain.energy_state import EnergyState

from ...telemetry.domain.test_telemetry import make_telemetry

SITE_ID = SiteId("SITE-1")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)
GRID = AnomalyType.GRID_INSTABILITY
INVERTER = AnomalyType.INVERTER_FAULT


class _FakeEvaluator:
    def __init__(self, report: EvaluationReport) -> None:
        self._report = report
        self.evaluated_with = None

    def evaluate(self, detector, previous_metrics):  # noqa: ANN001
        self.evaluated_with = (detector, previous_metrics)
        return self._report


class _FakeDetector:
    name = "fake-detector"
    version = "v1"

    def __init__(self) -> None:
        self.fit_called_with = None

    def detect(self, state, history):  # noqa: ANN001
        return []

    def fit(self, normal_history):  # noqa: ANN001
        self.fit_called_with = normal_history
        return FitResult(trained_on=len(normal_history), trained_at=NOW)


def _scenario(anomaly_type: AnomalyType, passed: bool) -> ScenarioResult:
    return ScenarioResult(
        scenario_name=anomaly_type.value,
        expected_type=anomaly_type,
        precision=1.0 if passed else 0.0,
        recall=1.0 if passed else 0.0,
        f1=1.0 if passed else 0.0,
        false_positive_rate=0.0,
        detection_latency_seconds=0.0,
        meets_targets=passed,
    )


def _report(*scenarios: ScenarioResult) -> EvaluationReport:
    return EvaluationReport(
        detector_name="fake-detector", detector_version="v1", scenario_results=scenarios
    )


def test_evaluate_and_register_registers_covered_types_on_pass():
    registry = InMemoryDetectorRegistry()
    evaluator = _FakeEvaluator(_report(_scenario(GRID, passed=True)))
    service = DetectorTrainingService(evaluator, registry)
    detector = _FakeDetector()

    outcome = service.evaluate_and_register(detector)

    assert outcome.registered is True
    assert outcome.covered_types == {GRID}
    assert registry.get_active() == [detector]
    assert registry.covered_types("fake-detector") == {GRID}


def test_evaluate_and_register_refuses_when_nothing_passes():
    registry = InMemoryDetectorRegistry()
    evaluator = _FakeEvaluator(_report(_scenario(GRID, passed=False)))
    service = DetectorTrainingService(evaluator, registry)
    detector = _FakeDetector()

    outcome = service.evaluate_and_register(detector)

    assert outcome.registered is False
    assert outcome.covered_types == frozenset()
    assert registry.get_active() == []


def test_evaluate_and_register_registers_only_the_passing_types():
    registry = InMemoryDetectorRegistry()
    evaluator = _FakeEvaluator(
        _report(_scenario(GRID, passed=True), _scenario(INVERTER, passed=False))
    )
    service = DetectorTrainingService(evaluator, registry)
    detector = _FakeDetector()

    outcome = service.evaluate_and_register(detector)

    assert outcome.registered is True
    assert outcome.covered_types == {GRID}
    assert registry.get_active() == [detector]
    assert registry.covered_types("fake-detector") == {GRID}


def test_train_and_evaluate_fits_before_evaluating():
    registry = InMemoryDetectorRegistry()
    evaluator = _FakeEvaluator(_report(_scenario(GRID, passed=True)))
    service = DetectorTrainingService(evaluator, registry)
    detector = _FakeDetector()
    history = [
        EnergyState.from_telemetry(
            make_telemetry(site_id=SITE_ID, timestamp=NOW), any_asset_offline=False
        )
    ]

    outcome = service.train_and_evaluate(detector, history)

    assert detector.fit_called_with == history
    assert outcome.registered is True


def test_previous_metrics_from_registry_are_passed_to_evaluator():
    registry = InMemoryDetectorRegistry()
    stale_detector = _FakeDetector()
    registry.register(stale_detector, {GRID}, {GRID: {"recall": 0.8}})

    evaluator = _FakeEvaluator(_report(_scenario(GRID, passed=True)))
    service = DetectorTrainingService(evaluator, registry)
    new_detector = _FakeDetector()

    service.evaluate_and_register(new_detector)

    assert evaluator.evaluated_with == (new_detector, {GRID: {"recall": 0.8}})
