"""In-memory AnomalyRepository — for tests and v1 (single-process, no persistence)."""

from __future__ import annotations

from datetime import datetime

from solarops.anomaly.domain.anomaly import Anomaly
from solarops.shared_kernel import SiteId

__all__ = ["InMemoryAnomalyRepository"]


class InMemoryAnomalyRepository:
    def __init__(self) -> None:
        self._anomalies: list[Anomaly] = []

    def save(self, anomaly: Anomaly) -> None:
        self._anomalies.append(anomaly)

    def list_recent(self, site_id: SiteId, *, since: datetime) -> list[Anomaly]:
        return [
            a for a in self._anomalies if a.site_id == site_id and a.detected_at >= since
        ]
