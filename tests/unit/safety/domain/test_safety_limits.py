import pytest

from solarops.safety.domain.safety_limits import SafetyLimits
from solarops.shared_kernel import GridStatus, InverterStatus, Power, StateOfCharge, Temperature


def make_limits(**overrides) -> SafetyLimits:
    defaults = dict(
        battery_min_soc=StateOfCharge(10.0),
        battery_max_soc=StateOfCharge(95.0),
        battery_max_temp=Temperature(45.0),
        battery_max_charge_power=Power(50.0),
        battery_max_discharge_power=Power(50.0),
        inverter_max_power=Power(120.0),
    )
    defaults.update(overrides)
    return SafetyLimits(**defaults)


def test_defaults_match_grid_model_and_normal_inverter_status():
    limits = make_limits()
    assert limits.inverter_allowed_statuses == frozenset({InverterStatus.NORMAL})
    assert limits.grid_required_status is GridStatus.CONNECTED
    assert limits.grid_nominal_voltage.value == 415.0
    assert limits.grid_nominal_frequency.value == 50.0
    assert limits.building_max_shed_fraction == 0.0


@pytest.mark.parametrize("fraction", [-0.01, 1.01])
def test_building_max_shed_fraction_must_be_within_zero_and_one(fraction):
    with pytest.raises(ValueError, match="building_max_shed_fraction"):
        make_limits(building_max_shed_fraction=fraction)


def test_limits_are_immutable():
    limits = make_limits()
    with pytest.raises(Exception):
        limits.battery_max_temp = Temperature(50.0)  # type: ignore[misc]
