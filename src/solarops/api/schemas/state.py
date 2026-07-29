"""EnergyState -> JSON. Serialization is the edge's job (Phase 7a brief §4) —
the domain's typed value objects (Power, Temperature, ...) are flattened to
plain numbers here, never in the domain."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from solarops.telemetry.domain.energy_state import EnergyState

__all__ = ["EnergyStateResponse"]


class EnergyStateResponse(BaseModel):
    site_id: str
    timestamp: datetime

    solar_power_kw: float
    solar_voltage_v: float
    solar_current_a: float
    irradiance_w_m2: float
    cloud_cover_pct: float
    ambient_temp_c: float

    battery_soc_pct: float
    battery_soh_pct: float
    battery_temp_c: float
    battery_power_kw: float
    battery_mode: str
    battery_cycle_count: float

    inverter_status: str
    inverter_temp_c: float
    inverter_output_kw: float

    grid_status: str
    grid_voltage_v: float
    grid_frequency_hz: float
    grid_power_kw: float

    building_load_kw: float
    fault_codes: list[str]
    net_power_kw: float
    any_asset_offline: bool

    @classmethod
    def from_domain(cls, state: EnergyState) -> EnergyStateResponse:
        return cls(
            site_id=str(state.site_id),
            timestamp=state.timestamp,
            solar_power_kw=state.solar_power.value,
            solar_voltage_v=state.solar_voltage.value,
            solar_current_a=state.solar_current.value,
            irradiance_w_m2=state.irradiance_w_m2,
            cloud_cover_pct=state.cloud_cover_pct,
            ambient_temp_c=state.ambient_temp.value,
            battery_soc_pct=state.battery_soc.value,
            battery_soh_pct=state.battery_soh_pct,
            battery_temp_c=state.battery_temp.value,
            battery_power_kw=state.battery_power.value,
            battery_mode=state.battery_mode.value,
            battery_cycle_count=state.battery_cycle_count,
            inverter_status=state.inverter_status.value,
            inverter_temp_c=state.inverter_temp.value,
            inverter_output_kw=state.inverter_output.value,
            grid_status=state.grid_status.value,
            grid_voltage_v=state.grid_voltage.value,
            grid_frequency_hz=state.grid_frequency.value,
            grid_power_kw=state.grid_power.value,
            building_load_kw=state.building_load.value,
            fault_codes=list(state.fault_codes),
            net_power_kw=state.net_power.value,
            any_asset_offline=state.any_asset_offline,
        )
