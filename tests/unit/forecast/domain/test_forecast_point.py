from datetime import UTC, datetime

import pytest

from solarops.forecast.domain.forecast_point import ForecastPoint
from solarops.shared_kernel import Power, StateOfCharge

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def test_accepts_power_value():
    point = ForecastPoint(timestamp=NOW, value=Power(42.0))
    assert point.value == Power(42.0)


def test_accepts_state_of_charge_value():
    point = ForecastPoint(timestamp=NOW, value=StateOfCharge(55.0))
    assert point.value.value == 55.0


def test_interval_defaults_to_none():
    point = ForecastPoint(timestamp=NOW, value=Power(10.0))
    assert point.interval_low is None
    assert point.interval_high is None


def test_is_immutable():
    point = ForecastPoint(timestamp=NOW, value=Power(10.0))
    with pytest.raises(Exception):
        point.value = Power(20.0)  # type: ignore[misc]
