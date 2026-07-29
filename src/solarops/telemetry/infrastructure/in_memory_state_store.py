"""In-memory StateStore — for tests and offline runs, no Redis required."""

from __future__ import annotations

from solarops.shared_kernel import SiteId
from solarops.telemetry.domain.energy_state import EnergyState


class InMemoryStateStore:
    """Dict-backed ``StateStore``. Not shared across processes — tests/dev only."""

    def __init__(self) -> None:
        self._states: dict[str, EnergyState] = {}

    def get(self, site_id: SiteId) -> EnergyState | None:
        return self._states.get(str(site_id))

    def set(self, state: EnergyState) -> None:
        self._states[str(state.site_id)] = state
