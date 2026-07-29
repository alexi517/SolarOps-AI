"""StateManager — Layer 1 working memory over the site's current EnergyState (Doc 8 §6.1)."""

from __future__ import annotations

from solarops.shared_kernel import SiteId
from solarops.telemetry.domain.energy_state import EnergyState
from solarops.telemetry.domain.events import EnergyStateUpdated
from solarops.telemetry.domain.ports import StateStore


class StateManager:
    """The single read/write point for a site's current ``EnergyState``.

    No event store exists yet (that's Observability-context infrastructure,
    Phase 7) — ``update()`` raises and returns the event rather than persisting
    it; a caller wires that up once a store exists.

    TODO(layer2): operational history (~24h of telemetry/commands/forecasts,
    Document 4 §3 "Layer 2") is not implemented — its definition lives in the
    SAS section that wasn't available when this context was built. This class
    is the seam where it will attach once that's confirmed.
    """

    def __init__(self, store: StateStore) -> None:
        self._store = store

    def get_current(self, site_id: SiteId) -> EnergyState | None:
        return self._store.get(site_id)

    def update(self, state: EnergyState) -> EnergyStateUpdated:
        self._store.set(state)
        return EnergyStateUpdated(
            aggregate_id=str(state.site_id),
            aggregate_type="Site",
            state_timestamp=state.timestamp,
        )
