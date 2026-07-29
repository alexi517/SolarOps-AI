"""Phase 6a end-to-end: train, gate, and produce forecasts — the swappable-interface proof.

1. Register the three deterministic baselines (the v1 default) through the
   Document 6 evaluation gate.
2. Generate training data by running the Digital Twin over a period disjoint
   from the six benchmark-scenario dates (no train/eval leakage), train
   ``XGBoostForecaster`` for Solar and Load, and run the same gate.
3. Two separate checks, deliberately not conflated:
   (a) the production path (forecaster -> ``ModelRegistry`` -> gate-registered
       model only) — proves the gate is actually enforced: a kind with nothing
       registered refuses to forecast rather than silently using an untested model.
   (b) direct model invocation through ``ForecastingService`` — proves the
       forecasting *machinery* itself genuinely produces all three kinds, at
       all four horizons, regardless of whether a given model happened to
       clear the Document 6 accuracy bar this run. A model failing the gate
       is a release-safety outcome, not evidence the pipeline is broken.
4. Prove the interface is genuinely swappable: the *same* baseline and
   XGBoost model objects trained above, called through the identical
   ``ForecastingService.generate`` signature.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from solarops.forecast.application.battery_soc_forecaster import BatterySocForecaster
from solarops.forecast.application.building_load_forecaster import BuildingLoadForecaster
from solarops.forecast.application.evaluation.forecast_evaluator import (
    EvaluationReport,
    ForecastEvaluator,
)
from solarops.forecast.application.feature_engineering import build_features
from solarops.forecast.application.forecasting_service import ForecastingService
from solarops.forecast.application.solar_generation_forecaster import SolarGenerationForecaster
from solarops.forecast.application.training.training_service import TrainingService
from solarops.forecast.domain.exceptions import NoRegisteredModel
from solarops.forecast.domain.feature_set import FeatureSet
from solarops.forecast.domain.forecast import Forecast
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.infrastructure.config import ForecastConfig
from solarops.forecast.infrastructure.in_memory_forecast_repository import (
    InMemoryForecastRepository,
)
from solarops.forecast.infrastructure.model_registry import InMemoryModelRegistry
from solarops.forecast.infrastructure.models.battery_soc_baseline import BatterySocBaseline
from solarops.forecast.infrastructure.models.load_baseline import LoadBaseline
from solarops.forecast.infrastructure.models.solar_baseline import SolarBaseline
from solarops.forecast.infrastructure.models.xgboost_forecaster import XGBoostForecaster
from solarops.platform.benchmark_scenario_source import generate_training_examples
from solarops.platform.forecast_wiring import (
    build_forecast_config,
    build_twin_benchmark_scenario_source,
    build_twin_historical_data_source,
    forecast_site_config,
)
from solarops.shared_kernel import FixedClock, SiteId
from solarops.simulation.domain.digital_twin import DigitalTwin
from solarops.simulation.infrastructure.config import SimulatorConfig, SiteConfig

SITE_ID = SiteId("site-001")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)

# Deliberately outside all six benchmark-scenario dates (2026-03-10, 2026-06-15,
# 2026-07-20) so XGBoost is never evaluated on the days it trained on.
TRAINING_PERIOD_START = datetime(2026, 1, 5, 6, 0)


def _report_line(report: EvaluationReport, registered: bool) -> str:
    verdict = "REGISTERED" if registered else "REJECTED"
    lines = [f"  [{verdict}] {report.model_name} {report.model_version} ({report.kind})"]
    for scenario in report.scenario_results:
        tag = "primary" if scenario.is_primary else "robustness"
        status = "PASS" if scenario.passed else "FAIL"
        lines.append(
            f"    {status:4} [{tag:10}] {scenario.scenario_name:20} "
            f"{scenario.metric_name}={scenario.metric_value:.2f} (target <= {scenario.target:.2f}) "
            f"ran_ok={scenario.ran_ok}"
        )
    if report.regressed:
        lines.append(f"    REGRESSION vs previous release: {report.previous_metric_value}")
    return "\n".join(lines)


def main() -> None:
    site_config = SiteConfig(site_id="site-001")
    config = build_forecast_config(site_config)

    repository = InMemoryForecastRepository()
    registry = InMemoryModelRegistry()
    clock = FixedClock(NOW)
    service = ForecastingService(repository, clock)

    historical_source = build_twin_historical_data_source(site_config, config)
    scenario_source = build_twin_benchmark_scenario_source(site_config, config)
    evaluator = ForecastEvaluator(scenario_source, config)
    training_service = TrainingService(evaluator, registry)

    print("=== Phase 6a: Forecasting Engine - training, evaluation gate, forecasts ===\n")

    # --- Step 1: baselines through the gate ---
    print("--- Registering baselines (v1 default) ---")
    baselines = {
        ForecastKind.SOLAR_GENERATION: SolarBaseline(
            capacity_kw=config.solar_capacity_kw, resolution_minutes=config.resolution_minutes
        ),
        ForecastKind.BUILDING_LOAD: LoadBaseline(resolution_minutes=config.resolution_minutes),
        ForecastKind.BATTERY_SOC: BatterySocBaseline(
            capacity_kwh=config.battery_capacity_kwh,
            round_trip_efficiency=config.battery_round_trip_efficiency,
            resolution_minutes=config.resolution_minutes,
        ),
    }
    for model in baselines.values():
        outcome = training_service.evaluate_and_register(model)
        print(_report_line(outcome.report, outcome.registered))
    print()

    # --- Step 2: XGBoost for Solar and Load, trained on a disjoint period ---
    print("--- Training XGBoostForecaster (Solar, Load) on a held-out training period ---")
    training_twin = DigitalTwin(
        site_config=forecast_site_config(site_config, config.resolution_minutes),
        simulator_config=SimulatorConfig(random_seed=7),
        start_time=TRAINING_PERIOD_START,
    )
    training_examples = generate_training_examples(training_twin, config)

    xgboost_models: dict[ForecastKind, XGBoostForecaster] = {}
    for kind, feature_names in (
        (ForecastKind.SOLAR_GENERATION, config.solar_features),
        (ForecastKind.BUILDING_LOAD, config.load_features),
    ):
        model = XGBoostForecaster(kind, feature_names, resolution_minutes=config.resolution_minutes)
        outcome = training_service.train_and_evaluate(model, training_examples[kind])
        xgboost_models[kind] = model  # fitted regardless of gate verdict
        print(_report_line(outcome.report, outcome.registered))
    print()

    history = historical_source.get_history(
        SITE_ID, as_of=NOW, lookback=timedelta(hours=config.lookback_hours)
    )
    current_state = history[-1] if history else None
    if current_state is None:
        print("  No history available - aborting.")
        return

    # --- Step 3a: the gate is actually enforced on the production path ---
    print("--- 3a. Production path (forecaster -> ModelRegistry): gate-registered models only ---")
    solar_forecaster = SolarGenerationForecaster(service, registry, historical_source, config)
    load_forecaster = BuildingLoadForecaster(service, registry, historical_source, config)
    battery_forecaster = BatterySocForecaster(service, registry, config)

    for label, action in (
        ("Solar generation", lambda: solar_forecaster.forecast(current_state)),
        ("Building load", lambda: load_forecaster.forecast(current_state)),
    ):
        try:
            forecast, _ = action()
            _print_forecast(label, forecast, config)
        except NoRegisteredModel as error:
            print(f"  {label}: correctly refused - {error}")
    try:
        registered_solar = registry.get_current(ForecastKind.SOLAR_GENERATION)
        registered_load = registry.get_current(ForecastKind.BUILDING_LOAD)
        if registered_solar is None or registered_load is None:
            raise NoRegisteredModel(ForecastKind.BATTERY_SOC)
        solar_fc, _ = solar_forecaster.forecast(current_state)
        load_fc, _ = load_forecaster.forecast(current_state)
        battery_forecast, _ = battery_forecaster.forecast(current_state, solar_fc, load_fc)
        _print_forecast("Battery SOC", battery_forecast, config)
    except NoRegisteredModel as error:
        print(f"  Battery SOC: correctly refused - {error}")

    # --- Step 3b: the machinery itself, invoked directly, regardless of gate verdict ---
    print(
        "\n--- 3b. Direct invocation through ForecastingService: all three kinds, all four "
        "horizons (independent of Step 1/2's gate verdicts above) ---"
    )
    solar_features_now = build_features(
        ForecastKind.SOLAR_GENERATION, current_state, history, config
    )
    load_features_now = build_features(
        ForecastKind.BUILDING_LOAD, current_state, history, config
    )

    solar_direct, _ = service.generate(
        SITE_ID, baselines[ForecastKind.SOLAR_GENERATION], solar_features_now,
        config.max_horizon_minutes, config.resolution_minutes,
    )
    load_direct, _ = service.generate(
        SITE_ID, baselines[ForecastKind.BUILDING_LOAD], load_features_now,
        config.max_horizon_minutes, config.resolution_minutes,
    )
    _print_forecast("Solar generation (baseline, direct)", solar_direct, config)
    _print_forecast("Building load (baseline, direct)", load_direct, config)

    avg_solar = sum(p.value.value for p in solar_direct.points) / len(solar_direct.points)
    avg_load = sum(p.value.value for p in load_direct.points) / len(load_direct.points)
    battery_features_now = FeatureSet(
        kind=ForecastKind.BATTERY_SOC,
        as_of=current_state.timestamp,
        values={
            "current_soc_pct": current_state.battery_soc.value,
            "avg_expected_solar_kw": avg_solar,
            "avg_expected_load_kw": avg_load,
        },
    )
    battery_direct, _ = service.generate(
        SITE_ID, baselines[ForecastKind.BATTERY_SOC], battery_features_now,
        config.max_horizon_minutes, config.resolution_minutes,
    )
    _print_forecast("Battery SOC (baseline, direct)", battery_direct, config)

    # --- Step 4: prove the interface is genuinely swappable ---
    print("\n--- Swappable-interface proof: same call, baseline vs. XGBoost, Solar Generation ---")
    solar_features_now = build_features(
        ForecastKind.SOLAR_GENERATION, current_state, history, config
    )
    baseline_model = baselines[ForecastKind.SOLAR_GENERATION]
    xgboost_model = xgboost_models[ForecastKind.SOLAR_GENERATION]

    baseline_forecast, _ = service.generate(
        SITE_ID, baseline_model, solar_features_now, config.max_horizon_minutes,
        config.resolution_minutes,
    )
    xgboost_forecast, _ = service.generate(
        SITE_ID, xgboost_model, solar_features_now, config.max_horizon_minutes,
        config.resolution_minutes,
    )
    print(f"  baseline ({baseline_model.name}) at +1h: {baseline_forecast.at_horizon(60).value}")
    print(f"  xgboost  ({xgboost_model.name}) at +1h: {xgboost_forecast.at_horizon(60).value}")
    print(
        "  Both produced through the identical ForecastingService.generate(site_id, model, "
        "features, horizon, resolution) call — only `model` differs. Whether XGBoost is *also* "
        "the one currently registered (Step 2) depends on whether it passed the gate this run; "
        "the interface swap itself does not depend on that."
    )


def _print_forecast(label: str, forecast: Forecast, config: ForecastConfig) -> None:
    print(f"\n  {label} - model {forecast.metadata.model_name} {forecast.metadata.model_version}")
    for horizon_label, horizon_minutes in config.named_horizons.items():
        point = forecast.at_horizon(horizon_minutes)
        print(f"    +{horizon_label:>5}: {point.value}")


if __name__ == "__main__":
    main()
