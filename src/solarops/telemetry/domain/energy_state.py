"""EnergyState — a consistent, immutable snapshot of the whole site (Doc 8 §5, §6.1).

Reconstructed by the Telemetry context from an ingested ``Telemetry`` reading —
it is the *interpreted* current state, not a re-export of raw telemetry. In v1,
with a single ``TelemetrySource`` (the Digital Twin), most fields carry straight
through; ``net_power`` and ``any_asset_offline`` are the interpretation this
context adds on top.

This is the single object downstream contexts (Forecast, Decision, Safety) read
— per Doc 8 §4, Telemetry -> {Forecast, Decision, Safety} is an Open Host
Service whose published language is exactly this snapshot.
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
from solarops.telemetry.domain.telemetry import Telemetry

__all__ = ["EnergyState"]


class EnergyState(BaseModel):
    """Immutable, consistent snapshot of the site's current observed state."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    site_id: SiteId
    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def _timestamp_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("EnergyState.timestamp must be timezone-aware")
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

    # --- reconstructed / interpreted, not present on the raw reading ---
    net_power: Power
    any_asset_offline: bool

    @classmethod
    def from_telemetry(cls, telemetry: Telemetry, *, any_asset_offline: bool) -> EnergyState:
        """Reconstruct the site's current state from one raw reading."""
        return cls(
            site_id=telemetry.site_id,
            timestamp=telemetry.timestamp,
            solar_power=telemetry.solar_power,
            solar_voltage=telemetry.solar_voltage,
            solar_current=telemetry.solar_current,
            irradiance_w_m2=telemetry.irradiance_w_m2,
            cloud_cover_pct=telemetry.cloud_cover_pct,
            ambient_temp=telemetry.ambient_temp,
            battery_soc=telemetry.battery_soc,
            battery_soh_pct=telemetry.battery_soh_pct,
            battery_temp=telemetry.battery_temp,
            battery_power=telemetry.battery_power,
            battery_mode=telemetry.battery_mode,
            battery_cycle_count=telemetry.battery_cycle_count,
            inverter_status=telemetry.inverter_status,
            inverter_temp=telemetry.inverter_temp,
            inverter_output=telemetry.inverter_output,
            grid_status=telemetry.grid_status,
            grid_voltage=telemetry.grid_voltage,
            grid_frequency=telemetry.grid_frequency,
            grid_power=telemetry.grid_power,
            building_load=telemetry.building_load,
            fault_codes=telemetry.fault_codes,
            net_power=Power(telemetry.solar_power.value - telemetry.building_load.value),
            any_asset_offline=any_asset_offline,
        )
