"""ForecastEvaluator — the Document 6 forecast metrics and release gate (brief §6).

Runs the six benchmark scenarios, scores a candidate model against the
``ForecastConfig`` targets, and checks for regression against the currently
released model's stored metrics. Clear Day / Cloud Front / Evening Peak are
the primary, accuracy-gating scenarios; Grid Outage / Battery Overheating /
Sensor Failure only need to run without the model crashing (brief §6 note).
"""

from __future__ import annotations

from dataclasses import dataclass

from solarops.forecast.application.evaluation.metrics import mae, mape
from solarops.forecast.domain.feature_set import TrainingExample
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.ports import BenchmarkScenarioSource, ForecastModel
from solarops.forecast.infrastructure.config import ForecastConfig

__all__ = ["ScenarioMetrics", "EvaluationReport", "ForecastEvaluator"]


@dataclass(frozen=True, slots=True)
class ScenarioMetrics:
    scenario_name: str
    is_primary: bool
    metric_name: str
    metric_value: float
    target: float
    ran_ok: bool = True

    @property
    def passed(self) -> bool:
        if not self.ran_ok:
            return False
        if not self.is_primary:
            return True
        return self.metric_value <= self.target


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    kind: ForecastKind
    model_name: str
    model_version: str
    scenario_results: tuple[ScenarioMetrics, ...]
    regressed: bool
    previous_metric_value: float | None

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.scenario_results) and not self.regressed

    @property
    def failed_scenarios(self) -> tuple[ScenarioMetrics, ...]:
        return tuple(r for r in self.scenario_results if not r.passed)

    @property
    def metrics_summary(self) -> dict[str, float]:
        """The figure worth persisting in the ModelRegistry for future regression checks."""
        primary = [r.metric_value for r in self.scenario_results if r.is_primary and r.ran_ok]
        if not primary:
            return {}
        metric_name = self.scenario_results[0].metric_name
        return {metric_name: sum(primary) / len(primary)}


_METRIC_BY_KIND: dict[ForecastKind, str] = {
    ForecastKind.SOLAR_GENERATION: "solar_mae_pct",
    ForecastKind.BUILDING_LOAD: "load_mape_pct",
    ForecastKind.BATTERY_SOC: "battery_soc_mae_pct",
}


class ForecastEvaluator:
    def __init__(self, scenario_source: BenchmarkScenarioSource, config: ForecastConfig) -> None:
        self._scenario_source = scenario_source
        self._config = config

    def evaluate(
        self, model: ForecastModel, previous_metrics: dict[str, float] | None
    ) -> EvaluationReport:
        kind = model.kind
        metric_name = _METRIC_BY_KIND[kind]
        target = self._target_for(kind)

        results: list[ScenarioMetrics] = []
        for scenario_name in self._scenario_source.scenario_names():
            run = self._scenario_source.run(scenario_name)
            examples = run.examples.get(kind, [])
            if not examples:
                continue
            try:
                actuals = [example.target for example in examples]
                predictions = [self._predict_at_horizon(model, example) for example in examples]
                metric_value = self._compute_metric(kind, actuals, predictions)
                ran_ok = True
            except Exception:  # a robustness scenario is allowed to be inaccurate, never to crash
                metric_value = float("inf")
                ran_ok = False
            results.append(
                ScenarioMetrics(
                    scenario_name=scenario_name,
                    is_primary=run.is_primary,
                    metric_name=metric_name,
                    metric_value=metric_value,
                    target=target,
                    ran_ok=ran_ok,
                )
            )

        previous_value = (previous_metrics or {}).get(metric_name)
        regressed = self._check_regression(results, previous_value)

        return EvaluationReport(
            kind=kind,
            model_name=model.name,
            model_version=model.version,
            scenario_results=tuple(results),
            regressed=regressed,
            previous_metric_value=previous_value,
        )

    def _predict_at_horizon(self, model: ForecastModel, example: TrainingExample) -> float:
        points = model.predict(example.features, example.horizon_minutes)
        return points[-1].value.value

    def _compute_metric(
        self, kind: ForecastKind, actuals: list[float], predictions: list[float]
    ) -> float:
        if kind is ForecastKind.SOLAR_GENERATION:
            raw_mae = mae(actuals, predictions)
            capacity = self._config.solar_capacity_kw
            return (raw_mae / capacity) * 100.0 if capacity > 0 else raw_mae
        if kind is ForecastKind.BUILDING_LOAD:
            return mape(actuals, predictions)
        if kind is ForecastKind.BATTERY_SOC:
            return mae(actuals, predictions)
        raise ValueError(f"unknown ForecastKind: {kind}")

    def _target_for(self, kind: ForecastKind) -> float:
        if kind is ForecastKind.SOLAR_GENERATION:
            return self._config.solar_mae_target_pct
        if kind is ForecastKind.BUILDING_LOAD:
            return self._config.load_mape_target_pct
        if kind is ForecastKind.BATTERY_SOC:
            return self._config.battery_soc_error_target_pct
        raise ValueError(f"unknown ForecastKind: {kind}")

    def _check_regression(
        self, results: list[ScenarioMetrics], previous_value: float | None
    ) -> bool:
        if previous_value is None:
            return False
        primary_values = [r.metric_value for r in results if r.is_primary and r.ran_ok]
        if not primary_values:
            return False
        current_avg = sum(primary_values) / len(primary_values)
        return current_avg > previous_value
