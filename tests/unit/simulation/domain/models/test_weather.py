from datetime import datetime

from solarops.simulation.domain.models.weather import WeatherModel


def test_irradiance_zero_at_midnight():
    weather = WeatherModel(seed=1)
    conditions = weather.step(datetime(2026, 7, 25, 0, 0))
    assert conditions.irradiance_w_m2 == 0.0


def test_irradiance_positive_at_noon():
    weather = WeatherModel(seed=1)
    conditions = weather.step(datetime(2026, 7, 25, 12, 0))
    assert conditions.irradiance_w_m2 > 500.0


def test_cloud_cover_injection_forces_value():
    weather = WeatherModel(seed=1)
    weather.inject_cloud_cover(90.0)
    conditions = weather.step(datetime(2026, 7, 25, 12, 0))
    assert conditions.cloud_cover_pct == 90.0

    weather.inject_cloud_cover(None)
    conditions_after = weather.step(datetime(2026, 7, 25, 12, 0, 5))
    assert conditions_after.cloud_cover_pct != 90.0
