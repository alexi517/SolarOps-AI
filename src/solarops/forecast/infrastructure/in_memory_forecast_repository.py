"""In-memory ForecastRepository — for tests and v1 (single-process, no persistence)."""

from __future__ import annotations

from solarops.forecast.domain.forecast import Forecast
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.shared_kernel import SiteId

__all__ = ["InMemoryForecastRepository"]


class InMemoryForecastRepository:
    def __init__(self) -> None:
        self._latest: dict[tuple[str, ForecastKind], Forecast] = {}

    def save(self, forecast: Forecast) -> None:
        self._latest[(str(forecast.site_id), forecast.kind)] = forecast

    def get_latest(self, site_id: SiteId, kind: ForecastKind) -> Forecast | None:
        return self._latest.get((str(site_id), kind))
