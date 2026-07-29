"""SimulationState — the Digital Twin's published telemetry (Document 8 §6.6).

Physical quantities are expressed with the shared kernel's value objects rather
than bare floats, per the DDD spec's "no primitive obsession" rule. A few fields
stay plain floats because the kernel has no corresponding unit for them (cloud
cover, irradiance, state of health, cycle count aren't in the shared vocabulary).

``BatteryMode``, ``InverterStatus``, and ``GridStatus`` live in the shared
kernel, not here — both Simulation (which produces them) and Telemetry (which
ingests them) need to agree on their meaning, which is exactly the "shared
vocabulary" case Document 8 §8 puts in the kernel.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from solarops.shared_kernel import (
    BatteryMode,
    Current,
    Frequency,
    GridStatus,
    InverterStatus,
    Power,
    SiteId,
    StateOfCharge,
    Temperature,
    Voltage,
)

__all__ = ["SimulationState"]


class SimulationState(BaseModel):
    """Immutable snapshot of the twin's internal physical state at one tick."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    timestamp: datetime
    site_id: SiteId

    solar_power: Power
    solar_voltage: Voltage
    solar_current: Current
    irradiance_w_m2: float
    cloud_cover_pct: float
    ambient_temp: Temperature

    battery_soc: StateOfCharge
    battery_soh_pct: float
    battery_temp: Temperature
    battery_power: Power
    battery_mode: BatteryMode
    battery_cycle_count: float

    inverter_status: InverterStatus
    inverter_temp: Temperature
    inverter_output: Power

    grid_status: GridStatus
    grid_voltage: Voltage
    grid_frequency: Frequency
    grid_power: Power

    building_load: Power

    fault_codes: list[str] = Field(default_factory=list)
