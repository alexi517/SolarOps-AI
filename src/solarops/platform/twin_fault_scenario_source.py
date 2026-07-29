"""TwinFaultScenarioSource — the Digital Twin's conformance to the Anomaly context's
``FaultScenarioSource`` port (Phase 6b brief §5).

Composition root: the one module allowed to import both ``solarops.simulation``
and ``solarops.anomaly`` for this purpose. Runs each fault scenario as a
normal-operation warmup, then injects the fault and keeps ticking, labelling
every reading — the ground truth ``AnomalyEvaluator`` scores a detector
against.
"""

from __future__ import annotations

from solarops.anomaly.domain.ports import FaultScenarioRun, LabeledReading
from solarops.platform.anomaly_fault_scenarios import anomaly_fault_scenario_definitions
from solarops.platform.twin_historical_data_source import simulation_state_to_energy_state
from solarops.simulation.domain.digital_twin import DigitalTwin
from solarops.simulation.infrastructure.config import SiteConfig

__all__ = ["TwinFaultScenarioSource"]

_WARMUP_TICKS = 20
_FAULT_TICKS = 60


class TwinFaultScenarioSource:
    def __init__(self, site_config: SiteConfig | None = None) -> None:
        self._definitions = {
            definition.name: definition
            for definition in anomaly_fault_scenario_definitions(site_config)
        }

    def scenario_names(self) -> list[str]:
        return list(self._definitions.keys())

    def run(self, scenario_name: str) -> FaultScenarioRun:
        definition = self._definitions[scenario_name]
        twin = DigitalTwin(
            site_config=definition.scenario.site_config,
            simulator_config=definition.scenario.simulator_config,
            start_time=definition.scenario.start_time,
        )

        readings: list[LabeledReading] = []
        for _ in range(_WARMUP_TICKS):
            state = simulation_state_to_energy_state(twin.tick())
            readings.append(LabeledReading(state=state, is_anomalous=False, expected_type=None))

        twin.inject_fault(definition.fault_target, definition.fault_code)

        for _ in range(_FAULT_TICKS):
            state = simulation_state_to_energy_state(twin.tick())
            readings.append(
                LabeledReading(
                    state=state, is_anomalous=True, expected_type=definition.expected_type
                )
            )

        return FaultScenarioRun(
            scenario_name=scenario_name,
            expected_type=definition.expected_type,
            readings=tuple(readings),
            tick_seconds=float(twin.site_config.update_interval_seconds),
        )
