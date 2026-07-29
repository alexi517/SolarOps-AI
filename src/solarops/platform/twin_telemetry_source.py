"""TwinTelemetrySource — the Digital Twin's conformance to the TelemetrySource port.

This is the composition root (Doc 8 §10, §6.8): the one module allowed to
import both ``solarops.simulation`` and ``solarops.telemetry``. It translates a
``SimulationState`` (Simulation's view of its own physics) into a ``Telemetry``
reading (what the Telemetry context ingests) — per Doc 8 §4, Simulation ->
Telemetry is an Open Host Service, so the twin exposes telemetry the same way a
real sensor would, and nothing downstream reaches into the twin directly.

``BatteryMode``/``InverterStatus``/``GridStatus`` are shared-kernel types (both
contexts import the same definitions — see ``shared_kernel/enums.py``), so no
enum translation is needed here, only field-by-field copying plus attaching
timezone-awareness to the twin's naive simulated clock.
"""

from __future__ import annotations

from datetime import UTC

from solarops.shared_kernel import SiteId
from solarops.simulation.domain.digital_twin import DigitalTwin
from solarops.telemetry.domain.telemetry import Telemetry


class TwinTelemetrySource:
    """Wraps a ``DigitalTwin``: each ``read()`` advances the twin one tick and
    returns that tick's state as a ``Telemetry`` reading."""

    def __init__(self, twin: DigitalTwin) -> None:
        self._twin = twin
        self._site_id = SiteId(twin.site_config.site_id)

    def read(self, site_id: SiteId) -> Telemetry:
        if site_id != self._site_id:
            raise ValueError(f"TwinTelemetrySource serves {self._site_id}, not {site_id}")

        sim_state = self._twin.tick()

        return Telemetry(
            site_id=self._site_id,
            timestamp=sim_state.timestamp.replace(tzinfo=UTC),
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
        )
