"""ForecastKind — which quantity a Forecast predicts (Doc 8 §6.2, Phase 6a brief §2)."""

from __future__ import annotations

from enum import StrEnum

__all__ = ["ForecastKind"]


class ForecastKind(StrEnum):
    SOLAR_GENERATION = "SOLAR_GENERATION"
    BUILDING_LOAD = "BUILDING_LOAD"
    BATTERY_SOC = "BATTERY_SOC"
