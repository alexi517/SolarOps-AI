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


def test_sunrise_and_sunset_track_nigeria_time_not_utc():
    # The twin's clock is UTC throughout the rest of the system, but this
    # site is in Nigeria (WAT, UTC+1) — sunrise/sunset should track 7am/7pm
    # WAT, i.e. 6am/6pm UTC, not 6am/6pm UTC taken literally.
    weather = WeatherModel(seed=1)

    just_before_sunrise_utc = weather.step(datetime(2026, 7, 25, 4, 30))  # 5:30am WAT
    assert just_before_sunrise_utc.irradiance_w_m2 == 0.0

    just_after_sunrise_utc = weather.step(datetime(2026, 7, 25, 5, 30))  # 6:30am WAT
    assert just_after_sunrise_utc.irradiance_w_m2 > 0.0

    just_before_sunset_utc = weather.step(datetime(2026, 7, 25, 16, 30))  # 5:30pm WAT
    assert just_before_sunset_utc.irradiance_w_m2 > 0.0

    just_after_sunset_utc = weather.step(datetime(2026, 7, 25, 17, 30))  # 6:30pm WAT
    assert just_after_sunset_utc.irradiance_w_m2 == 0.0


def test_cloud_cover_injection_forces_value():
    weather = WeatherModel(seed=1)
    weather.inject_cloud_cover(90.0)
    conditions = weather.step(datetime(2026, 7, 25, 12, 0))
    assert conditions.cloud_cover_pct == 90.0

    weather.inject_cloud_cover(None)
    conditions_after = weather.step(datetime(2026, 7, 25, 12, 0, 5))
    assert conditions_after.cloud_cover_pct != 90.0
