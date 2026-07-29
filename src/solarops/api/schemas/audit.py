"""EventEnvelope -> JSON — the immutable audit trail (brief §2)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from solarops.shared_kernel import EventEnvelope

__all__ = ["AuditEntryResponse"]


class AuditEntryResponse(BaseModel):
    event_id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    occurred_at: datetime
    correlation_id: str | None

    @classmethod
    def from_domain(cls, entry: EventEnvelope) -> AuditEntryResponse:
        return cls(
            event_id=entry.event_id,
            event_type=entry.event_type,
            aggregate_id=entry.aggregate_id,
            aggregate_type=entry.aggregate_type,
            occurred_at=entry.occurred_at,
            correlation_id=entry.correlation_id,
        )
