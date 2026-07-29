"""TwinHistoricalDataSource — the Digital Twin's conformance to the Forecast context's
``HistoricalDataSource`` port (Phase 6a brief §7).

Composition root (Doc 8 §10, §6.8): the one module allowed to import both
``solarops.simulation`` and ``solarops.forecast`` for this purpose. Generates
synthetic training/feature history by running a fresh ``DigitalTwin`` from
``as_of - lookback`` forward to ``as_of`` — the interim source Phase 6a is
built against (Forecast never imports Simulation directly).

``simulation_state_to_energy_state`` is exported so ``benchmark_scenario_source.py``
(the other twin-driven Forecast adapter) reuses the same mapping rather than a
second hand-copy of every field.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from solarops.shared_kernel import Power, SiteId
from solarops.simulation.domain.digital_twin import DigitalTwin
from solarops.simulation.domain.simulation_state import SimulationState
from solarops.simulation.infrastructure.config import SimulatorConfig, SiteConfig
from solarops.telemetry.domain.energy_state import EnergyState

__all__ = ["TwinHistoricalDataSource", "simulation_state_to_energy_state"]


def simulation_state_to_energy_state(sim_state: SimulationState) -> EnergyState:
    timestamp = sim_state.timestamp
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return EnergyState(
        site_id=sim_state.site_id,
        timestamp=timestamp,
        solar_power=sim_state.solar_power,
        solar_voltage=sim_state.solar_voltage,
        solar_current=sim_state.solar_current,
        irradiance_w_m2=sim_state.irradiance_w_m2,
        cloud_cover_pct=sim_state.cloud_cover_pct,
        ambient_temp=sim_state.ambient_temp,
        battery_soc=sim_state.battery_soc,
        battery_soh_pct=sim_state.battery_soh_pct,
        battery_temp=sim_state.battery_temp,
        battery_power=sim_state.battery_power,
        battery_mode=sim_state.battery_mode,
        battery_cycle_count=sim_state.battery_cycle_count,
        inverter_status=sim_state.inverter_status,
        inverter_temp=sim_state.inverter_temp,
        inverter_output=sim_state.inverter_output,
        grid_status=sim_state.grid_status,
        grid_voltage=sim_state.grid_voltage,
        grid_frequency=sim_state.grid_frequency,
        grid_power=sim_state.grid_power,
        building_load=sim_state.building_load,
        fault_codes=sim_state.fault_codes,
        net_power=Power(sim_state.solar_power.value - sim_state.building_load.value),
        any_asset_offline=False,
    )


class TwinHistoricalDataSource:
    """Runs the twin over ``lookback`` to produce an ``EnergyState`` history ending at ``as_of``."""

    def __init__(
        self, site_config: SiteConfig, simulator_config: SimulatorConfig | None = None
    ) -> None:
        self._site_config = site_config
        self._simulator_config = simulator_config or SimulatorConfig()
        self._site_id = SiteId(site_config.site_id)

    def get_history(
        self, site_id: SiteId, *, as_of: datetime, lookback: timedelta
    ) -> list[EnergyState]:
        if site_id != self._site_id:
            raise ValueError(f"TwinHistoricalDataSource serves {self._site_id}, not {site_id}")

        start_time = (as_of - lookback).replace(tzinfo=None)
        twin = DigitalTwin(
            site_config=self._site_config,
            simulator_config=self._simulator_config,
            start_time=start_time,
        )
        step_seconds = self._site_config.update_interval_seconds
        step_count = max(1, int(lookback.total_seconds() // step_seconds))

        return [simulation_state_to_energy_state(twin.tick()) for _ in range(step_count)]
