import pytest

from solarops.decision.domain.operating_constraints import OperatingConstraints
from solarops.shared_kernel import Power, StateOfCharge, Temperature


def make_constraints(**overrides) -> OperatingConstraints:
    defaults = dict(
        max_battery_soc=StateOfCharge(95.0),
        min_battery_soc=StateOfCharge(10.0),
        battery_max_temp=Temperature(45.0),
        battery_max_charge_power=Power(50.0),
        battery_max_discharge_power=Power(50.0),
        maintenance_mode=False,
        max_shed_fraction=0.3,
    )
    defaults.update(overrides)
    return OperatingConstraints(**defaults)


def test_constructs_with_valid_fields():
    constraints = make_constraints()
    assert constraints.max_battery_soc.value == 95.0
    assert constraints.maintenance_mode is False


def test_rejects_shed_fraction_outside_unit_interval():
    with pytest.raises(ValueError, match="max_shed_fraction"):
        make_constraints(max_shed_fraction=1.5)


def test_is_immutable():
    constraints = make_constraints()
    with pytest.raises(Exception):
        constraints.maintenance_mode = True  # type: ignore[misc]
