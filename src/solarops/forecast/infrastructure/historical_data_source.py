"""InMemoryHistoricalDataSource — list-backed, simulation-agnostic (brief §4/§7).

The context-local, always-tested implementation. The real, twin-driving
implementation (``TwinHistoricalDataSource``) lives at the platform
composition root, since generating synthetic history means running the
Digital Twin, and Forecast may not import Simulation (brief §8).
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
