"""Postgres-backed AuditLog — durable audit trail (CESF §15, Phase 8 brief §3).

Mirrors ``InMemoryAuditLog`` exactly: stores only ``EventEnvelope``'s routing
header (event id/type, aggregate id/type, occurred_at, correlation_id), never
the full event payload — that boundary was already established by the
in-memory version and confirmed as the *complete* existing contract by
checking ``api/schemas/audit.py``, which only ever surfaces envelope fields
too. This only changes where the six columns are kept, not what's kept.

Plain SQLAlchemy Core (a ``Table`` plus explicit ``insert``/``select``
statements), not the ORM — this can't be run against a real Postgres in the
environment it was written in, so it's kept to the simplest thing that's
easy to verify by reading it.

Same append-only guarantee as the in-memory version: no update/delete method
exists on this class — that omission *is* the "no audit entry can be
altered" guarantee, structural rather than a runtime check.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, MetaData, String, Table, insert, select
from sqlalchemy.engine import Engine

from solarops.shared_kernel import DomainEvent, EventEnvelope

__all__ = ["PostgresAuditLog", "AUDIT_LOG_METADATA", "audit_log_table"]

AUDIT_LOG_METADATA = MetaData()

audit_log_table = Table(
    "audit_log",
    AUDIT_LOG_METADATA,
    Column("event_id", String, primary_key=True),
    Column("event_type", String, nullable=False),
    Column("aggregate_id", String, nullable=False, index=True),
    Column("aggregate_type", String, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("correlation_id", String, nullable=True),
)


class PostgresAuditLog:
    """``AuditLog`` backed by a real Postgres table.

    The table is created (if missing) on construction — one append-only
    table doesn't warrant a separate migration tool for Phase 8's scope
    (dockerize, not introduce a migration framework).
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        AUDIT_LOG_METADATA.create_all(engine, checkfirst=True)

    def append(self, event: DomainEvent) -> None:
        envelope = EventEnvelope.of(event)
        with self._engine.begin() as connection:
            connection.execute(
                insert(audit_log_table).values(
                    event_id=envelope.event_id,
                    event_type=envelope.event_type,
                    aggregate_id=envelope.aggregate_id,
                    aggregate_type=envelope.aggregate_type,
                    occurred_at=envelope.occurred_at,
                    correlation_id=envelope.correlation_id,
                )
            )

    def all(self) -> tuple[EventEnvelope, ...]:
        with self._engine.connect() as connection:
            rows = connection.execute(select(audit_log_table)).mappings().all()
        return tuple(self._row_to_envelope(row) for row in rows)

    def for_aggregate(self, aggregate_id: str) -> tuple[EventEnvelope, ...]:
        statement = select(audit_log_table).where(
            audit_log_table.c.aggregate_id == aggregate_id
        )
        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return tuple(self._row_to_envelope(row) for row in rows)

    @staticmethod
    def _row_to_envelope(row) -> EventEnvelope:
        return EventEnvelope(
            event_id=row["event_id"],
            event_type=row["event_type"],
            aggregate_id=row["aggregate_id"],
            aggregate_type=row["aggregate_type"],
            occurred_at=row["occurred_at"],
            correlation_id=row["correlation_id"],
        )
