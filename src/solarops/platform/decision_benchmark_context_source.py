"""DecisionBenchmarkContextSource — the Digital Twin's conformance to Decision's
``BenchmarkContextSource`` port (Phase 6c brief §7).

Composition root: spans Simulation and Decision, which is orchestration,
neither context may import directly. Reuses the six Document 6 §9 scenario
definitions built in 6a (``platform/benchmark_scenarios.py``); ticks each
scenario's twin a few times (applying its fault, where one is defined) and
wraps the resulting ``EnergyState`` into a ``DecisionContext`` with the
site's real ``OperatingConstraints``. No forecasts are attached here — this
evaluation harness exercises decision *logic*, not forecast integration.
"""

from __future__ import annotations

from solarops.decision.domain.decision_context import DecisionContext
from solarops.platform.benchmark_scenarios import benchmark_scenario_definitions
from solarops.platform.decision_wiring import build_operating_constraints
from solarops.platform.safety_wiring import build_policy, build_safety_limits
from solarops.platform.twin_historical_data_source import simulation_state_to_energy_state
from solarops.simulation.infrastructure.config import SiteConfig

__all__ = ["DecisionBenchmarkContextSource"]

# Deep enough into each scenario that fault-driven faults have actually
# manifested (e.g. the Battery Overheating scenario's thermal ramp crosses a
# typical 45C limit around tick ~15 at the twin's default 5s resolution —
# same ramp-time finding as the Phase 6b cleanup pass), not just started.
_WARMUP_TICKS = 20


class DecisionBenchmarkContextSource:
    def __init__(self, site_config: SiteConfig | None = None) -> None:
        config = site_config or SiteConfig()
        self._definitions = {
            definition.name: definition
            for definition in benchmark_scenario_definitions(config)
        }
        self._operating_constraints = build_operating_constraints(
            build_policy(config), build_safety_limits(config)
        )

    def scenario_names(self) -> list[str]:
        return list(self._definitions.keys())

    def context_for(self, scenario_name: str) -> DecisionContext:
        definition = self._definitions[scenario_name]
        twin = definition.build_twin()
        state = None
        for _ in range(_WARMUP_TICKS):
            state = simulation_state_to_energy_state(twin.tick())
        return DecisionContext(
            energy_state=state, operating_constraints=self._operating_constraints
        )
