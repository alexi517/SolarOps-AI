"""Scenario — a named configuration driving the Digital Twin (Document 8 §6.6)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from solarops.shared_kernel import ScenarioId
from solarops.simulation.infrastructure.config import SimulatorConfig, SiteConfig


@dataclass(frozen=True, slots=True)
class Scenario:
    """Bundles the configuration and starting point for one simulation run."""

    scenario_id: ScenarioId
    name: str
    site_config: SiteConfig
    simulator_config: SimulatorConfig
    start_time: datetime
