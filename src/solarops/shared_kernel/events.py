"""Domain events — the published language between contexts.

Every meaningful state change emits a ``DomainEvent``. The Observability context
consumes these to build the immutable audit trail and metrics, and the workflow
layer can react to them. The base carries only cross-cutting metadata (identity,
time, correlation); concrete events add their own fields and live in the context
that owns the aggregate.

Payload *serialisation* is deliberately not the kernel's job — that belongs to
the infrastructure event store (Phase 3). ``EventEnvelope`` here captures only
the routing metadata every event shares.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from .ids import EventId

__all__ = ["DomainEvent", "EventEnvelope"]


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Immutable base for all domain events.

    ``kw_only`` means subclasses can add required fields without fighting
    dataclass default-ordering rules. ``event_type`` derives from the concrete
    class name so it never drifts from the code.
    """

    aggregate_id: str
    aggregate_type: str
    event_id: EventId = field(default_factory=EventId.generate)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str | None = None

    @property
    def event_type(self) -> str:
        return type(self).__name__


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    """Routing metadata for an event as it enters the event store.

    This is the persisted *header*; the full serialised payload is added by the
    infrastructure layer that owns the storage format.
    """

    event_id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    occurred_at: datetime
    correlation_id: str | None

    @classmethod
    def of(cls, event: DomainEvent) -> EventEnvelope:
        return cls(
            event_id=str(event.event_id),
            event_type=event.event_type,
            aggregate_id=event.aggregate_id,
            aggregate_type=event.aggregate_type,
            occurred_at=event.occurred_at,
            correlation_id=event.correlation_id,
        )
