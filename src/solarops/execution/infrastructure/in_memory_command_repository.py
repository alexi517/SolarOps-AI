"""In-memory CommandRepository — for tests and v1 (single-process, no persistence)."""

from __future__ import annotations

from solarops.execution.domain.command import Command
from solarops.shared_kernel import CommandId, SiteId


class InMemoryCommandRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, Command] = {}
        self._by_idempotency_key: dict[str, Command] = {}

    def get(self, command_id: CommandId) -> Command | None:
        return self._by_id.get(str(command_id))

    def get_by_idempotency_key(self, idempotency_key: str) -> Command | None:
        return self._by_idempotency_key.get(idempotency_key)

    def list_by_site(self, site_id: SiteId) -> list[Command]:
        return [c for c in self._by_id.values() if c.site_id == site_id]

    def save(self, command: Command) -> None:
        self._by_id[str(command.command_id)] = command
        self._by_idempotency_key[command.idempotency_key] = command
