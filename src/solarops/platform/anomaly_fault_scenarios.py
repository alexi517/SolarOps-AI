"""The five Document 6 §5 fault scenarios (Phase 6b brief §5).

Reuses three of Forecast's Document 6 §9 benchmark scenarios by name (Battery
Overheating, Grid Outage, Sensor Failure — including the Sensor Failure
"solar OFFLINE" stand-in disclosed in the Phase 6a plan) and adds two new
ones (Inverter Fault, Communication Loss) using twin fault codes that already
exist — no twin changes needed.

Unlike Forecast's ``BenchmarkScenarioDefinition`` (whose fault is applied at
twin construction, since Forecast's evaluation doesn't need a before/after
transition), Anomaly's evaluation needs ground truth labelled *around* the
moment the fault starts — so the fault here is metadata only.
``twin_fault_scenario_source.py`` builds a clean twin, ticks a normal
-operation warmup, injects the fault, and keeps ticking.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.shared_kernel import ScenarioId
from solarops.simulation.domain.digital_twin import FaultTarget
from solarops.simulation.domain.scenario import Scenario
from solarops.simulation.infrastructure.config import SimulatorConfig, SiteConfig

__all__ = ["AnomalyFaultScenarioDefinition", "anomaly_fault_scenario_definitions"]


@dataclass(frozen=True, slots=True)
class AnomalyFaultScenarioDefinition:
    name: str
    scenario: Scenario
    fault_target: FaultTarget
    fault_code: str
    expected_type: AnomalyType


def _scenario(name: str, start_time: datetime, site_config: SiteConfig) -> Scenario:
    return Scenario(
        scenario_id=ScenarioId.generate(),
        name=name,
        site_config=site_config,
        simulator_config=SimulatorConfig(),
        start_time=start_time,
    )


def anomaly_fault_scenario_definitions(
    site_config: SiteConfig | None = None,
) -> list[AnomalyFaultScenarioDefinition]:
    """The five fault scenarios, built against ``site_config`` (or its defaults)."""
    config = site_config or SiteConfig()

    return [
        AnomalyFaultScenarioDefinition(
            name="Battery Overheating",
            scenario=_scenario(
                "Battery Overheating", datetime(2026, 7, 20, 12, 0, tzinfo=UTC), config
            ),
            fault_target="battery",
            fault_code="OVERHEATING",
            expected_type=AnomalyType.BATTERY_OVERHEATING,
        ),
        AnomalyFaultScenarioDefinition(
            name="Grid Outage",
            scenario=_scenario("Grid Outage", datetime(2026, 6, 15, 10, 0, tzinfo=UTC), config),
            fault_target="grid",
            fault_code="OUTAGE",
            expected_type=AnomalyType.GRID_INSTABILITY,
        ),
        AnomalyFaultScenarioDefinition(
            name="Sensor Failure",
            scenario=_scenario("Sensor Failure", datetime(2026, 6, 15, 10, 0, tzinfo=UTC), config),
            fault_target="solar",
            fault_code="OFFLINE",
            expected_type=AnomalyType.SENSOR_FAILURE,
        ),
        AnomalyFaultScenarioDefinition(
            name="Inverter Fault",
            scenario=_scenario("Inverter Fault", datetime(2026, 6, 15, 10, 0, tzinfo=UTC), config),
            fault_target="inverter",
            fault_code="FAULT_OVERTEMP",
            expected_type=AnomalyType.INVERTER_FAULT,
        ),
        AnomalyFaultScenarioDefinition(
            name="Communication Loss",
            scenario=_scenario(
                "Communication Loss", datetime(2026, 6, 15, 10, 0, tzinfo=UTC), config
            ),
            fault_target="inverter",
            fault_code="FAULT_COMM_LOSS",
            expected_type=AnomalyType.COMMUNICATION_LOSS,
        ),
    ]
