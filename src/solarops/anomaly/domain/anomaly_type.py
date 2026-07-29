"""AnomalyType — the six fault categories to detect.

Phase 6b brief §2, from the PRD/ASDS task list.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["AnomalyType"]


class AnomalyType(StrEnum):
    BATTERY_OVERHEATING = "BATTERY_OVERHEATING"
    SENSOR_FAILURE = "SENSOR_FAILURE"
    COMMUNICATION_LOSS = "COMMUNICATION_LOSS"
    LOAD_SPIKE = "LOAD_SPIKE"
    INVERTER_FAULT = "INVERTER_FAULT"
    GRID_INSTABILITY = "GRID_INSTABILITY"
