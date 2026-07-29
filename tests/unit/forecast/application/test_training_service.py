from datetime import UTC, datetime

from solarops.forecast.application.evaluation.forecast_evaluator import (
    EvaluationReport,
    ScenarioMetrics,
)
from solarops.forecast.application.training.training_service import TrainingService
from solarops.forecast.domain.feature_set import FeatureSet, TrainingExample
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.forecast_point import ForecastPoint
from solarops.forecast.domain.ports import FitResult
from solarops.forecast.infrastructure.model_registry import InMemoryModelRegistry
from solarops.shared_kernel import Power

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


class _FakeEvaluator:
    def __init__(self, report: EvaluationReport) -> None:
        self._report = report
        self.evaluated_with: object | None = None

    def evaluate(self, model, previous_metrics):  # noqa: ANN001
        self.evaluated_with = (model, previous_metrics)
        return self._report


class _FakeModel:
    name = "fake"
    version = "v1"
    kind = ForecastKind.SOLAR_GENERATION
    fit_called_with: list[TrainingExample] | None = None

    def predict(self, features: FeatureSet, horizon_minutes: int) -> list[ForecastPoint]:
        return [ForecastPoint(timestamp=features.as_of, value=Power(1.0))]

    def fit(self, training_set: list[TrainingExample]) -> FitResult:
        self.fit_called_with = training_set
        return FitResult(trained_on=len(training_set), trained_at=NOW)


def _report(passed: bool, kind=ForecastKind.SOLAR_GENERATION) -> EvaluationReport:
    scenario = ScenarioMetrics(
        scenario_name="Clear Day",
        is_primary=True,
        metric_name="solar_mae_pct",
        metric_value=1.0 if passed else 20.0,
        target=8.0,
    )
    return EvaluationReport(
        kind=kind,
        model_name="fake",
        model_version="v1",
        scenario_results=(scenario,),
        regressed=False,
        previous_metric_value=None,
    )


def test_evaluate_and_register_registers_on_pass():
    registry = InMemoryModelRegistry()
    evaluator = _FakeEvaluator(_report(passed=True))
    service = TrainingService(evaluator, registry)
    model = _FakeModel()

    outcome = service.evaluate_and_register(model)

    assert outcome.registered is True
    assert registry.get_current(ForecastKind.SOLAR_GENERATION) is model


def test_evaluate_and_register_refuses_on_fail():
    registry = InMemoryModelRegistry()
    evaluator = _FakeEvaluator(_report(passed=False))
    service = TrainingService(evaluator, registry)
    model = _FakeModel()

    outcome = service.evaluate_and_register(model)

    assert outcome.registered is False
    assert registry.get_current(ForecastKind.SOLAR_GENERATION) is None


def _make_training_set(model: _FakeModel) -> list[TrainingExample]:
    features = FeatureSet(kind=model.kind, as_of=NOW)
    return [TrainingExample(features=features, horizon_minutes=15, target=1.0)]


def test_train_and_evaluate_fits_before_evaluating():
    registry = InMemoryModelRegistry()
    evaluator = _FakeEvaluator(_report(passed=True))
    service = TrainingService(evaluator, registry)
    model = _FakeModel()
    training_set = _make_training_set(model)

    outcome = service.train_and_evaluate(model, training_set)

    assert model.fit_called_with == training_set
    assert outcome.registered is True


def test_retrain_delegates_to_train_and_evaluate():
    registry = InMemoryModelRegistry()
    evaluator = _FakeEvaluator(_report(passed=True))
    service = TrainingService(evaluator, registry)
    model = _FakeModel()
    training_set = _make_training_set(model)

    outcome = service.retrain(model, training_set)

    assert model.fit_called_with == training_set
    assert outcome.registered is True


def test_previous_metrics_from_registry_are_passed_to_evaluator():
    registry = InMemoryModelRegistry()
    stale_model = _FakeModel()
    registry.register(stale_model, {"solar_mae_pct": 3.0})

    evaluator = _FakeEvaluator(_report(passed=True))
    service = TrainingService(evaluator, registry)
    new_model = _FakeModel()

    service.evaluate_and_register(new_model)

    assert evaluator.evaluated_with == (new_model, {"solar_mae_pct": 3.0})
