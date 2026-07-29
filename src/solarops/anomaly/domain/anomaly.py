"""Anomaly — aggregate root, the Anomaly context's published language (Phase 6b brief §3).

Every ``Anomaly`` carries exactly the six fields the task list requires
(``anomaly_type``, ``severity``, ``confidence``, ``affected_asset``,
``supporting_evidence``, ``recommended_action``), plus identity/provenance
(``anomaly_id``, ``site_id``, ``detected_at``) — the same pattern ``Forecast``
uses for its required domain fields plus bookkeeping (Doc 8 §6.2).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.domain.severity import Severity
from solarops.shared_kernel import AnomalyId, AssetId, SiteId

__all__ = ["Anomaly"]


class Anomaly(BaseModel):
    """A single, scored, explainable anomaly — ready to alert on."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    anomaly_id: AnomalyId
    site_id: SiteId
    detected_at: datetime

    anomaly_type: AnomalyType
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    affected_asset: AssetId
    supporting_evidence: tuple[str, ...]
    recommended_action: str

    @field_validator("detected_at")
    @classmethod
    def _detected_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Anomaly.detected_at must be timezone-aware")
        return value

    @field_validator("supporting_evidence")
    @classmethod
    def _evidence_must_not_be_empty(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("Anomaly.supporting_evidence must not be empty")
        return value
