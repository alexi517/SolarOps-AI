"""explanation.py — recommended_action text per AnomalyType (brief §4).

Simple deterministic templates, not the full Document 6 §8 explainability
framework (why/why-now/evidence/alternatives/risks) — the brief only asks for
a ``recommended_action`` field on ``Anomaly``, populated here.
"""

from __future__ import annotations

from solarops.anomaly.domain.anomaly_type import AnomalyType

__all__ = ["recommended_action_for"]

_TEMPLATES: dict[AnomalyType, str] = {
    AnomalyType.BATTERY_OVERHEATING: (
        "Reduce battery charge/discharge current immediately and inspect cooling."
    ),
    AnomalyType.SENSOR_FAILURE: (
        "Dispatch a technician to inspect the sensor; treat its telemetry as "
        "unreliable until resolved."
    ),
    AnomalyType.COMMUNICATION_LOSS: (
        "Attempt to reconnect the affected asset; escalate to on-call if not "
        "restored shortly."
    ),
    AnomalyType.LOAD_SPIKE: (
        "Verify the load increase is expected; consider shedding non-critical "
        "load if it persists."
    ),
    AnomalyType.INVERTER_FAULT: (
        "Take the inverter offline for inspection; verify no downstream overcurrent."
    ),
    AnomalyType.GRID_INSTABILITY: (
        "Prepare to island onto battery/backup power; notify the operator."
    ),
}


def recommended_action_for(anomaly_type: AnomalyType) -> str:
    return _TEMPLATES[anomaly_type]
