import math
import random
from dataclasses import dataclass
from datetime import datetime

PEAK_IRRADIANCE_W_M2 = 1000.0
SUNRISE_HOUR = 6.0
SUNSET_HOUR = 18.0

# This site is in Nigeria — WAT (West Africa Time) is a fixed UTC+1 with no
# daylight saving, so a constant offset is correct year-round (no timezone
# database needed). The twin's own clock (DigitalTwin._time) stays true UTC
# throughout the rest of the system — every other timestamp (EnergyState,
# Command.created_at, audit entries, ...) depends on that; only *this*
# model's day/night calculation needs to see Nigeria's local hour instead.
SITE_UTC_OFFSET_HOURS = 1.0


def _clear_sky_irradiance(hour_of_day: float) -> float:
    """Bell-curve irradiance between sunrise and sunset, peaking at solar noon."""
    if hour_of_day <= SUNRISE_HOUR or hour_of_day >= SUNSET_HOUR:
        return 0.0
    daylight_fraction = (hour_of_day - SUNRISE_HOUR) / (SUNSET_HOUR - SUNRISE_HOUR)
    return PEAK_IRRADIANCE_W_M2 * math.sin(math.pi * daylight_fraction)


def _ambient_temp(hour_of_day: float) -> float:
    """Simple diurnal temperature curve, coolest before dawn, warmest mid-afternoon."""
    return 18.0 + 10.0 * max(0.0, math.sin(math.pi * (hour_of_day - 5.0) / 18.0))


@dataclass
class WeatherConditions:
    irradiance_w_m2: float
    cloud_cover_pct: float
    ambient_temp_c: float


class WeatherModel:
    """Simulates solar irradiance, cloud cover, and ambient temperature over time."""

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)
        self._cloud_cover_pct = 10.0
        self._forced_cloud_cover_pct: float | None = None

    def step(self, timestamp: datetime) -> WeatherConditions:
        utc_hour_of_day = timestamp.hour + timestamp.minute / 60.0 + timestamp.second / 3600.0
        hour_of_day = (utc_hour_of_day + SITE_UTC_OFFSET_HOURS) % 24.0

        if self._forced_cloud_cover_pct is not None:
            self._cloud_cover_pct = self._forced_cloud_cover_pct
        else:
            drift = self._rng.uniform(-3.0, 3.0)
            self._cloud_cover_pct = min(100.0, max(0.0, self._cloud_cover_pct + drift))

        base_irradiance = _clear_sky_irradiance(hour_of_day)
        irradiance = base_irradiance * (1.0 - 0.75 * self._cloud_cover_pct / 100.0)

        return WeatherConditions(
            irradiance_w_m2=round(irradiance, 2),
            cloud_cover_pct=round(self._cloud_cover_pct, 1),
            ambient_temp_c=round(_ambient_temp(hour_of_day), 1),
        )

    def inject_cloud_cover(self, cloud_cover_pct: float | None) -> None:
        """Force cloud cover to a fixed value (fault injection). Pass None to release."""
        self._forced_cloud_cover_pct = cloud_cover_pct
