from datetime import UTC, datetime

from solarops.forecast.application.evaluation.forecast_evaluator import ForecastEvaluator
from solarops.forecast.domain.feature_set import FeatureSet, TrainingExample
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.forecast_point import ForecastPoint
from solarops.forecast.domain.ports import BenchmarkRun
from solarops.forecast.infrastructure.config import ForecastConfig
from solarops.shared_kernel import Power

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


class _FakeScenarioSource:
    def __init__(self, runs: dict[str, BenchmarkRun]) -> None:
        self._runs = runs

    def scenario_names(self) -> list[str]:
        return list(self._runs.keys())

    def run(self, scenario_name: str) -> BenchmarkRun:
        return self._runs[scenario_name]


class _FakeSolarModel:
    name = "fake-solar"
    version = "v1"
    kind = ForecastKind.SOLAR_GENERATION

    def __init__(self, predicted_kw: float, crash_on_marker: bool = False) -> None:
        self._predicted_kw = predicted_kw
        self._crash_on_marker = crash_on_marker

    def predict(self, features: FeatureSet, horizon_minutes: int) -> list[ForecastPoint]:
        if self._crash_on_marker and features.values.get("should_crash") == 1.0:
            raise RuntimeError("simulated crash")
        return [ForecastPoint(timestamp=features.as_of, value=Power(self._predicted_kw))]


def _example(target: float, marker: dict | None = None) -> TrainingExample:
    features = FeatureSet(
        kind=ForecastKind.SOLAR_GENERATION, as_of=NOW, values=dict(marker or {})
    )
    return TrainingExample(features=features, horizon_minutes=60, target=target)


def _primary_runs(target: float) -> dict[str, BenchmarkRun]:
    return {
        name: BenchmarkRun(
            scenario_name=name,
            is_primary=True,
            examples={ForecastKind.SOLAR_GENERATION: [_example(target)]},
        )
        for name in ("Clear Day", "Cloud Front", "Evening Peak")
    }


def test_accurate_model_passes_the_gate():
    config = ForecastConfig(solar_capacity_kw=100.0, solar_mae_target_pct=8.0)
    runs = _primary_runs(target=50.0)
    evaluator = ForecastEvaluator(_FakeScenarioSource(runs), config)

    report = evaluator.evaluate(_FakeSolarModel(predicted_kw=50.0), previous_metrics=None)

    assert report.passed is True
    assert report.failed_scenarios == ()


def test_inaccurate_model_fails_the_gate():
    config = ForecastConfig(solar_capacity_kw=100.0, solar_mae_target_pct=8.0)
    runs = _primary_runs(target=50.0)
    evaluator = ForecastEvaluator(_FakeScenarioSource(runs), config)

    report = evaluator.evaluate(_FakeSolarModel(predicted_kw=0.0), previous_metrics=None)

    assert report.passed is False
    assert len(report.failed_scenarios) == 3


def test_regression_against_previous_release_blocks_the_gate():
    config = ForecastConfig(solar_capacity_kw=100.0, solar_mae_target_pct=8.0)
    runs = _primary_runs(target=50.0)
    evaluator = ForecastEvaluator(_FakeScenarioSource(runs), config)

    # predicted=48 -> MAE=2 -> 2% of 100kW capacity: within the 8% target...
    report = evaluator.evaluate(
        _FakeSolarModel(predicted_kw=48.0), previous_metrics={"solar_mae_pct": 0.5}
    )

    # ...but worse than the previous release's 0.5% -> regression blocks it anyway.
    assert report.regressed is True
    assert report.passed is False


def test_robustness_scenario_crash_blocks_the_gate_even_if_primary_scenarios_pass():
    config = ForecastConfig(solar_capacity_kw=100.0, solar_mae_target_pct=8.0)
    runs = _primary_runs(target=50.0)
    runs["Grid Outage"] = BenchmarkRun(
        scenario_name="Grid Outage",
        is_primary=False,
        examples={ForecastKind.SOLAR_GENERATION: [_example(50.0, marker={"should_crash": 1.0})]},
    )
    evaluator = ForecastEvaluator(_FakeScenarioSource(runs), config)

    report = evaluator.evaluate(
        _FakeSolarModel(predicted_kw=50.0, crash_on_marker=True), previous_metrics=None
    )

    assert report.passed is False
    crashed = [r for r in report.scenario_results if r.scenario_name == "Grid Outage"][0]
    assert crashed.ran_ok is False


def test_metrics_summary_averages_primary_scenarios_only():
    config = ForecastConfig(solar_capacity_kw=100.0, solar_mae_target_pct=8.0)
    runs = _primary_runs(target=50.0)
    evaluator = ForecastEvaluator(_FakeScenarioSource(runs), config)

    report = evaluator.evaluate(_FakeSolarModel(predicted_kw=50.0), previous_metrics=None)

    assert report.metrics_summary == {"solar_mae_pct": 0.0}
