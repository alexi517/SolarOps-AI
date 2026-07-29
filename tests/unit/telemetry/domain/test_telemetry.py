from datetime import UTC, datetime

import pytest

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


def make_telemetry(**overrides):
    defaults = dict(
        site_id=SiteId("SITE-1"),
        timestamp=datetime(2026, 7, 27, 12, 0, tzinfo=UTC),
        solar_power=Power(50.0),
        solar_voltage=Voltage(600.0),
        solar_current=Current(83.3),
        irradiance_w_m2=800.0,
        cloud_cover_pct=10.0,
        ambient_temp=Temperature(28.0),
        battery_soc=StateOfCharge(60.0),
        battery_soh_pct=99.5,
        battery_temp=Temperature(30.0),
        battery_power=Power(10.0),
        battery_mode=BatteryMode.CHARGING,
        battery_cycle_count=1.2,
        inverter_status=InverterStatus.NORMAL,
        inverter_temp=Temperature(35.0),
        inverter_output=Power(48.0),
        grid_status=GridStatus.CONNECTED,
        grid_voltage=Voltage(415.0),
        grid_frequency=Frequency(50.0),
        grid_power=Power(5.0),
        building_load=Power(40.0),
    )
    defaults.update(overrides)
    return Telemetry(**defaults)


def test_telemetry_round_trips_kernel_value_objects():
    telemetry = make_telemetry()
    assert telemetry.solar_power == Power(50.0)
    assert telemetry.battery_soc.value == 60.0
    assert telemetry.battery_mode is BatteryMode.CHARGING


def test_telemetry_rejects_naive_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        make_telemetry(timestamp=datetime(2026, 7, 27, 12, 0))


def test_telemetry_is_immutable():
    telemetry = make_telemetry()
    with pytest.raises(Exception):
        telemetry.battery_soc = StateOfCharge(10.0)  # type: ignore[misc]
