"""Telemetry — one immutable reading (Document 8 §6.1).

Holds exactly what a ``TelemetrySource`` reported for one site at one moment —
nothing derived, nothing interpreted. ``EnergyState`` (built from this) is the
reconstructed, interpreted snapshot; keeping them distinct types matters even in
v1, where there's only one source, because it's what lets a second real sensor
be added later without redefining what "current state" means.

``BatteryMode``, ``InverterStatus``, and ``GridStatus`` come from the shared
kernel — both Simulation and Telemetry need to agree on their meaning, so they
aren't duplicated per context (Document 8 §8).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

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

__all__ = ["Telemetry"]


class Telemetry(BaseModel):
    """One raw, unvalidated-beyond-construction reading from a ``TelemetrySource``."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    site_id: SiteId
    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def _timestamp_must_be_aware(cls, value: datetime) -> datetime:
        # Mirrors the kernel Clock contract: every timestamp crossing a context
        # boundary is timezone-aware UTC, never naive wall/sim time.
        if value.tzinfo is None:
            raise ValueError("Telemetry.timestamp must be timezone-aware")
        return value

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
