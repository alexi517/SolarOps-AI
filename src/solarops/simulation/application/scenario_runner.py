"""ScenarioRunner — application-layer use case: drive a DigitalTwin through a Scenario."""

from __future__ import annotations

from solarops.simulation.domain.digital_twin import DigitalTwin
from solarops.simulation.domain.scenario import Scenario
from solarops.simulation.domain.simulation_state import SimulationState


class ScenarioRunner:
    """Builds a ``DigitalTwin`` from a ``Scenario`` and drives it forward."""

    def __init__(self, scenario: Scenario) -> None:
        self.scenario = scenario
        self.twin = DigitalTwin(
            site_config=scenario.site_config,
            simulator_config=scenario.simulator_config,
            start_time=scenario.start_time,
        )

    def run(self, steps: int) -> list[SimulationState]:
        return self.twin.run(steps)
