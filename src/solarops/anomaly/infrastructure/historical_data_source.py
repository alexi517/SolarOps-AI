"""InMemoryHistoricalDataSource — list-backed, simulation-agnostic (brief §4/§7).

Anomaly's own port type — structurally identical to Forecast's equivalent,
but a separate definition: bounded contexts don't share code across the
import boundary (Anomaly may not import Forecast). The real, twin-driving
implementation is ``platform.twin_historical_data_source.TwinHistoricalDataSource``
(built in 6a), reused as-is — it already satisfies this shape.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from solarops.shared_kernel import SiteId
from solarops.telemetry.domain.energy_state import EnergyState

__all__ = ["InMemoryHistoricalDataSource"]


class InMemoryHistoricalDataSource:
    def __init__(self, history: list[EnergyState] | None = None) -> None:
        self._history: dict[str, list[EnergyState]] = {}
        for state in history or []:
            self.add(state)

    def add(self, state: EnergyState) -> None:
        self._history.setdefault(str(state.site_id), []).append(state)

    def get_history(
        self, site_id: SiteId, *, as_of: datetime, lookback: timedelta
    ) -> list[EnergyState]:
        cutoff = as_of - lookback
        states = self._history.get(str(site_id), [])
        in_window = [s for s in states if cutoff <= s.timestamp <= as_of]
        return sorted(in_window, key=lambda s: s.timestamp)
