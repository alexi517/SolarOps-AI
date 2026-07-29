import math
import random
from datetime import datetime

OCCUPANCY_START_HOUR = 6.0
OCCUPANCY_END_HOUR = 22.0
NIGHT_LOAD_FRACTION = 0.05
WEEKEND_LOAD_MULTIPLIER = 0.4


def _occupancy_factor(hour_of_day: float) -> float:
    if hour_of_day <= OCCUPANCY_START_HOUR or hour_of_day >= OCCUPANCY_END_HOUR:
        return NIGHT_LOAD_FRACTION
    daylight_fraction = (hour_of_day - OCCUPANCY_START_HOUR) / (OCCUPANCY_END_HOUR - OCCUPANCY_START_HOUR)
    return max(NIGHT_LOAD_FRACTION, math.sin(math.pi * daylight_fraction))


class BuildingLoadModel:
    """Simulates commercial building electrical demand based on time of day and occupancy."""

    def __init__(self, baseline_kw: float, peak_kw: float, seed: int | None = None):
        self.baseline_kw = baseline_kw
        self.peak_kw = peak_kw
        self._rng = random.Random(seed)
        self._shed_fraction = 0.0

    def step(self, timestamp: datetime) -> float:
        hour_of_day = timestamp.hour + timestamp.minute / 60.0
        occupancy = _occupancy_factor(hour_of_day)

        if timestamp.weekday() >= 5:
            occupancy *= WEEKEND_LOAD_MULTIPLIER

        noise = self._rng.uniform(-0.05, 0.05)
        load_kw = self.baseline_kw + (self.peak_kw - self.baseline_kw) * max(0.0, occupancy + noise)
        load_kw *= 1.0 - self._shed_fraction

        return round(max(0.0, load_kw), 2)

    def shed_load(self, fraction: float) -> None:
        """Shed a fraction (0-1) of non-critical load."""
        self._shed_fraction = max(0.0, min(1.0, fraction))

    def restore_load(self) -> None:
        self._shed_fraction = 0.0
