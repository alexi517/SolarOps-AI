from datetime import datetime

import pytest

from solarops.shared_kernel import BatteryMode, GridStatus, InverterStatus, Power
from solarops.telemetry.domain.energy_state import EnergyState

from .test_telemetry import make_telemetry


def test_from_telemetry_carries_fields_through():
    telemetry = make_telemetry()
    state = EnergyState.from_telemetry(telemetry, any_asset_offline=False)

    assert state.site_id == telemetry.site_id
    assert state.timestamp == telemetry.timestamp
    assert state.solar_power == telemetry.solar_power
    assert state.battery_soc == telemetry.battery_soc
    assert state.battery_mode is BatteryMode.CHARGING
    assert state.grid_status is GridStatus.CONNECTED
    assert state.inverter_status is InverterStatus.NORMAL
    assert state.any_asset_offline is False


def test_net_power_is_solar_minus_building_load():
    telemetry = make_telemetry(solar_power=Power(80.0), building_load=Power(30.0))
    state = EnergyState.from_telemetry(telemetry, any_asset_offline=False)
    assert state.net_power == Power(50.0)


def test_energy_state_rejects_naive_timestamp():
    telemetry = make_telemetry()
    kwargs = telemetry.model_dump(mode="python")
    kwargs["timestamp"] = datetime(2026, 7, 27, 12, 0)  # naive
    kwargs["net_power"] = Power(0.0)
    kwargs["any_asset_offline"] = False
    with pytest.raises(ValueError, match="timezone-aware"):
        EnergyState(**kwargs)


def test_energy_state_is_immutable():
    state = EnergyState.from_telemetry(make_telemetry(), any_asset_offline=False)
    with pytest.raises(Exception):
        state.any_asset_offline = True  # type: ignore[misc]
