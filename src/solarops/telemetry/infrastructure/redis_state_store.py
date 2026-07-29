"""Redis-backed StateStore — Layer 1 working memory (Document 4 §3)."""

from __future__ import annotations

import redis

from solarops.shared_kernel import SiteId
from solarops.telemetry.domain.energy_state import EnergyState

DEFAULT_KEY_PREFIX = "state"


class RedisStateStore:
    """``StateStore`` backed by Redis. Serialisation is an infrastructure concern
    — the domain never sees JSON."""

    def __init__(self, client: redis.Redis, key_prefix: str = DEFAULT_KEY_PREFIX) -> None:
        self._client = client
        self._key_prefix = key_prefix

    def _key(self, site_id: SiteId) -> str:
        return f"{self._key_prefix}:{site_id}"

    def get(self, site_id: SiteId) -> EnergyState | None:
        raw = self._client.get(self._key(site_id))
        if raw is None:
            return None
        return EnergyState.model_validate_json(raw)

    def set(self, state: EnergyState) -> None:
        self._client.set(self._key(state.site_id), state.model_dump_json())
