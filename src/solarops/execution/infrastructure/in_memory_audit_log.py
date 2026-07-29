"""In-memory audit log — append + read only, no delete (CESF §15).

Stores the shared kernel's ``EventEnvelope`` (the persisted-header type
already built for exactly this — see the Phase 5 plan's gap #4) rather than a
new ``AuditEntry`` type invented ahead of the Observability context (Doc 8
§6.7, Phase 7), which owns real durable audit storage.

No delete/remove method exists on this class — that omission *is* the "no
command can be deleted" guarantee (§15), structural rather than a runtime check.
"""

from __future__ import annotations

from solarops.shared_kernel import DomainEvent, EventEnvelope


class InMemoryAuditLog:
    def __init__(self) -> None:
        self._entries: list[EventEnvelope] = []

    def append(self, event: DomainEvent) -> None:
        self._entries.append(EventEnvelope.of(event))

    def all(self) -> tuple[EventEnvelope, ...]:
        return tuple(self._entries)

    def for_aggregate(self, aggregate_id: str) -> tuple[EventEnvelope, ...]:
        return tuple(e for e in self._entries if e.aggregate_id == aggregate_id)
