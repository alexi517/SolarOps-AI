"""The six Document 6 §9 benchmark scenarios, reusing Simulation's ``Scenario`` aggregate.

Composition root: imports both ``simulation`` (for ``Scenario``/fault
injection) and ``forecast`` (only via ``benchmark_scenario_source.py``, which
consumes these definitions) — the evaluation harness spans both, which is
orchestration, not something either context may do itself (Phase 6a brief §8).

``Scenario`` (Doc 8 §6.6) bundles configuration and a start time; it carries no
fault-injection or "expected AI response" concept of its own, so each
definition here pairs one with the ``DigitalTwin.inject_fault``/
``inject_weather_fault`` calls that give it its scenario character.

Clear Day / Cloud Front / Evening Peak are the primary, accuracy-gating
scenarios (brief §6); Grid Outage / Battery Overheating / Sensor Failure only
need to run without the pipeline crashing. The twin has no real "sensor
failure" fault (``inject_fault("sensor", ...)`` only clears a weather
override) — Sensor Failure is stood up as ``inject_fault("solar", "OFFLINE")``,
a flatlined reading being the closest available analogue to a dead sensor,
disclosed here rather than silently chosen (Phase 6a plan, judgment call #3).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from solarops.shared_kernel import ScenarioId
from solarops.simulation.domain.digital_twin import DigitalTwin, FaultTarget
from solarops.simulation.domain.scenario import Scenario
from solarops.simulation.infrastructure.config import SimulatorConfig, SiteConfig

__all__ = ["BenchmarkScenarioDefinition", "benchmark_scenario_definitions"]


@dataclass(frozen=True, slots=True)
class BenchmarkScenarioDefinition:
    name: str
    is_primary: bool
    scenario: Scenario
    faults: tuple[tuple[FaultTarget, str | None], ...] = ()
    weather_cloud_override_pct: float | None = None

    def build_twin(self) -> DigitalTwin:
        twin = DigitalTwin(
            site_config=self.scenario.site_config,
            simulator_config=self.scenario.simulator_config,
            start_time=self.scenario.start_time,
        )
        for target, fault in self.faults:
            twin.inject_fault(target, fault)
        if self.weather_cloud_override_pct is not None:
            twin.inject_weather_fault(self.weather_cloud_override_pct)
        return twin


def _scenario(name: str, start_time: datetime, site_config: SiteConfig) -> Scenario:
    return Scenario(
        scenario_id=ScenarioId.generate(),
        name=name,
        site_config=site_config,
        simulator_config=SimulatorConfig(),
        start_time=start_time,
    )


def benchmark_scenario_definitions(
    site_config: SiteConfig | None = None,
) -> list[BenchmarkScenarioDefinition]:
    """The six benchmark scenarios, built against ``site_config`` (or its defaults)."""
    config = site_config or SiteConfig()

    return [
        BenchmarkScenarioDefinition(
            name="Clear Day",
            is_primary=True,
            scenario=_scenario("Clear Day", datetime(2026, 6, 15, 6, 0, tzinfo=UTC), config),
            weather_cloud_override_pct=0.0,
        ),
        BenchmarkScenarioDefinition(
            name="Cloud Front",
            is_primary=True,
            scenario=_scenario("Cloud Front", datetime(2026, 3, 10, 6, 0, tzinfo=UTC), config),
            weather_cloud_override_pct=70.0,
        ),
        BenchmarkScenarioDefinition(
            name="Evening Peak",
            is_primary=True,
            scenario=_scenario("Evening Peak", datetime(2026, 6, 15, 14, 0, tzinfo=UTC), config),
        ),
        BenchmarkScenarioDefinition(
            name="Grid Outage",
            is_primary=False,
            scenario=_scenario("Grid Outage", datetime(2026, 6, 15, 10, 0, tzinfo=UTC), config),
            faults=(("grid", "OUTAGE"),),
        ),
        BenchmarkScenarioDefinition(
            name="Battery Overheating",
            is_primary=False,
            scenario=_scenario(
                "Battery Overheating", datetime(2026, 7, 20, 12, 0, tzinfo=UTC), config
            ),
            faults=(("battery", "OVERHEATING"),),
        ),
        BenchmarkScenarioDefinition(
            name="Sensor Failure",
            is_primary=False,
            scenario=_scenario("Sensor Failure", datetime(2026, 6, 15, 10, 0, tzinfo=UTC), config),
            faults=(("solar", "OFFLINE"),),
        ),
    ]
