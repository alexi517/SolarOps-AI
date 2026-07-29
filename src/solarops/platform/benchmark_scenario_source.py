"""TwinBenchmarkScenarioSource — the Digital Twin's conformance to the Forecast
context's ``BenchmarkScenarioSource`` port (Phase 6a brief §6).

Composition root: runs each of the six named scenarios (``benchmark_scenarios.py``)
through the twin, sampling several (features-at-T, actuals-after-T) checkpoints
per scenario as ``TrainingExample`` ground truth for ``ForecastEvaluator``.

``generate_training_examples`` is exported separately so the *training* data
generator (``scripts/run_forecast_training_and_evaluation.py``) can run the
exact same "tick the twin, pair features-at-T with actuals-after-T" logic over
its own, disjoint simulated period — training a model on the same days it is
later benchmarked against would leak the evaluation into the training set.
"""

from __future__ import annotations

from solarops.forecast.application.feature_engineering import build_features
from solarops.forecast.domain.feature_set import FeatureSet, TrainingExample
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.ports import BenchmarkRun
from solarops.forecast.infrastructure.config import ForecastConfig
from solarops.platform.benchmark_scenarios import benchmark_scenario_definitions
from solarops.platform.twin_historical_data_source import simulation_state_to_energy_state
from solarops.simulation.domain.digital_twin import DigitalTwin
from solarops.simulation.infrastructure.config import SiteConfig
from solarops.telemetry.domain.energy_state import EnergyState

__all__ = ["TwinBenchmarkScenarioSource", "generate_training_examples"]

_CHECKPOINTS_PER_RUN = 4


def generate_training_examples(
    twin: DigitalTwin, config: ForecastConfig
) -> dict[ForecastKind, list[TrainingExample]]:
    """Tick ``twin`` forward, pairing features-at-T with actuals-after-T for every
    configured horizon, for all three forecast kinds."""
    lookback_steps = max(
        1, int(config.lookback_hours * 3600 // twin.site_config.update_interval_seconds)
    )
    history: list[EnergyState] = [
        simulation_state_to_energy_state(twin.tick()) for _ in range(lookback_steps)
    ]

    max_horizon_steps = config.max_horizon_minutes // config.resolution_minutes
    examples: dict[ForecastKind, list[TrainingExample]] = {kind: [] for kind in ForecastKind}

    for _ in range(_CHECKPOINTS_PER_RUN):
        current_state = simulation_state_to_energy_state(twin.tick())
        history.append(current_state)

        future_states = [
            simulation_state_to_energy_state(twin.tick()) for _ in range(max_horizon_steps)
        ]
        history.extend(future_states)

        for horizon_minutes in config.horizons_minutes:
            step_index = horizon_minutes // config.resolution_minutes - 1
            if not (0 <= step_index < len(future_states)):
                continue
            actual_state = future_states[step_index]
            _add_examples(
                examples, config, current_state, history, future_states[: step_index + 1],
                actual_state, horizon_minutes,
            )

    return examples


def _add_examples(
    examples: dict[ForecastKind, list[TrainingExample]],
    config: ForecastConfig,
    current_state: EnergyState,
    history: list[EnergyState],
    states_up_to_horizon: list[EnergyState],
    actual_state: EnergyState,
    horizon_minutes: int,
) -> None:
    solar_features = build_features(ForecastKind.SOLAR_GENERATION, current_state, history, config)
    examples[ForecastKind.SOLAR_GENERATION].append(
        TrainingExample(
            features=solar_features,
            horizon_minutes=horizon_minutes,
            target=actual_state.solar_power.value,
        )
    )

    load_features = build_features(ForecastKind.BUILDING_LOAD, current_state, history, config)
    examples[ForecastKind.BUILDING_LOAD].append(
        TrainingExample(
            features=load_features,
            horizon_minutes=horizon_minutes,
            target=actual_state.building_load.value,
        )
    )

    avg_solar = sum(s.solar_power.value for s in states_up_to_horizon) / len(states_up_to_horizon)
    avg_load = sum(s.building_load.value for s in states_up_to_horizon) / len(states_up_to_horizon)
    battery_features = FeatureSet(
        kind=ForecastKind.BATTERY_SOC,
        as_of=current_state.timestamp,
        values={
            "current_soc_pct": current_state.battery_soc.value,
            "avg_expected_solar_kw": avg_solar,
            "avg_expected_load_kw": avg_load,
        },
    )
    examples[ForecastKind.BATTERY_SOC].append(
        TrainingExample(
            features=battery_features,
            horizon_minutes=horizon_minutes,
            target=actual_state.battery_soc.value,
        )
    )


class TwinBenchmarkScenarioSource:
    def __init__(self, config: ForecastConfig, site_config: SiteConfig | None = None) -> None:
        self._config = config
        self._definitions = {
            definition.name: definition
            for definition in benchmark_scenario_definitions(site_config)
        }

    def scenario_names(self) -> list[str]:
        return list(self._definitions.keys())

    def run(self, scenario_name: str) -> BenchmarkRun:
        definition = self._definitions[scenario_name]
        twin = definition.build_twin()
        examples = generate_training_examples(twin, self._config)
        return BenchmarkRun(
            scenario_name=scenario_name, is_primary=definition.is_primary, examples=examples
        )
