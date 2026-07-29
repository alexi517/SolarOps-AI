"""InMemoryAlertPublisher — records published Alerts (brief §6, Option A: detect-and-alert only).

This is the disclosed seam: a real Observability context would implement
``AlertPublisher`` to fan out to logs/dashboards; Option B (feeding Decision)
would attach a second implementation or subscriber to the same
``AlertRaised`` event stream — neither is built in 6b.
"""

from __future__ import annotations

from solarops.anomaly.domain.anomaly import Anomaly

__all__ = ["InMemoryAlertPublisher"]


class InMemoryAlertPublisher:
    def __init__(self) -> None:
        self.published: list[Anomaly] = []

    def publish(self, anomaly: Anomaly) -> None:
        self.published.append(anomaly)
