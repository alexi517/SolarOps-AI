"""Tests for physical-quantity value objects."""

from __future__ import annotations

import pytest

from solarops.shared_kernel.units import (
    Current,
    Energy,
    Power,
    StateOfCharge,
    Temperature,
    Voltage,
)


def test_construction_and_value() -> None:
    assert Power(12.5).value == 12.5
    assert Energy(0.0).value == 0.0


def test_equality_within_type() -> None:
    assert Power(3.0) == Power(3.0)
    assert Power(3.0) != Power(4.0)


def test_different_quantity_types_are_never_equal() -> None:
    assert Power(1.0) != Energy(1.0)


def test_addition_and_subtraction_same_type() -> None:
    assert Power(2.0) + Power(3.0) == Power(5.0)
    assert Power(5.0) - Power(2.0) == Power(3.0)


def test_adding_different_types_is_a_type_error() -> None:
    with pytest.raises(TypeError):
        _ = Power(1.0) + Energy(1.0)  # type: ignore[operator]


def test_scalar_multiplication_is_commutative() -> None:
    assert Power(2.0) * 3 == Power(6.0)
    assert 3 * Power(2.0) == Power(6.0)


def test_division_by_scalar_and_by_same_type() -> None:
    assert Power(6.0) / 2 == Power(3.0)
    # dividing like by like yields a dimensionless ratio
    assert Power(6.0) / Power(2.0) == 3.0


def test_negation_and_absolute_value() -> None:
    assert -Power(4.0) == Power(-4.0)
    assert abs(Power(-4.0)) == Power(4.0)


def test_ordering_within_type() -> None:
    assert Power(1.0) < Power(2.0)
    assert Power(2.0) >= Power(2.0)
    assert sorted([Power(3.0), Power(1.0), Power(2.0)]) == [Power(1.0), Power(2.0), Power(3.0)]


def test_comparing_different_types_raises() -> None:
    with pytest.raises(TypeError):
        _ = Power(1.0) < Energy(2.0)  # type: ignore[operator]


def test_bounds_are_enforced() -> None:
    with pytest.raises(ValueError):
        Energy(-0.1)
    with pytest.raises(ValueError):
        StateOfCharge(-1.0)
    with pytest.raises(ValueError):
        StateOfCharge(100.01)
    with pytest.raises(ValueError):
        Voltage(-1.0)


def test_bounds_allow_the_edges() -> None:
    assert StateOfCharge(0.0).value == 0.0
    assert StateOfCharge(100.0).value == 100.0


def test_signed_quantities_allow_negatives() -> None:
    # Power and Current use sign for direction.
    assert Power(-5.0).value == -5.0
    assert Current(-2.0).value == -2.0


def test_nan_and_inf_are_rejected() -> None:
    with pytest.raises(ValueError):
        Power(float("nan"))
    with pytest.raises(ValueError):
        Power(float("inf"))


def test_bool_is_not_a_valid_number() -> None:
    with pytest.raises(TypeError):
        Power(True)  # type: ignore[arg-type]


def test_state_of_charge_fraction() -> None:
    assert StateOfCharge(50.0).fraction == 0.5
    assert StateOfCharge(0.0).fraction == 0.0
    assert StateOfCharge(100.0).fraction == 1.0


def test_str_includes_unit() -> None:
    assert str(Power(12.5)) == "12.5 kW"
    assert str(StateOfCharge(85.0)) == "85 %"
    assert str(Temperature(21.0)).endswith("C")


def test_value_object_is_immutable() -> None:
    p = Power(1.0)
    with pytest.raises(Exception):
        p.value = 2.0  # type: ignore[misc]


def test_quantities_are_hashable() -> None:
    assert len({Power(1.0), Power(1.0), Power(2.0)}) == 2
