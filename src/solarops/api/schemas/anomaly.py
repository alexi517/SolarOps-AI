"""Anomaly -> JSON — the six required fields (brief §2)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from solarops.anomaly.domain.anomaly import Anomaly

__all__ = ["AnomalyResponse"]


class AnomalyResponse(BaseModel):
    anomaly_id: str
    site_id: str
    detected_at: datetime
    anomaly_type: str
    severity: str
    confidence: float
    affected_asset: str
    supporting_evidence: list[str]
    recommended_action: str

    @classmethod
    def from_domain(cls, anomaly: Anomaly) -> AnomalyResponse:
        return cls(
            anomaly_id=str(anomaly.anomaly_id),
            site_id=str(anomaly.site_id),
            detected_at=anomaly.detected_at,
            anomaly_type=anomaly.anomaly_type.value,
            severity=anomaly.severity.value,
            confidence=anomaly.confidence,
            affected_asset=str(anomaly.affected_asset),
            supporting_evidence=list(anomaly.supporting_evidence),
            recommended_action=anomaly.recommended_action,
        )
