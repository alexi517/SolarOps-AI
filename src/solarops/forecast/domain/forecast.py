"""Forecast — aggregate root, the Forecast context's published language (Doc 8 §6.2).

Crosses into Decision (Phase 6c) as an immutable contract, the same pattern
``Recommendation`` uses for Execution (Doc 8 §4): Decision reads a ``Forecast``,
it never reaches into how one was produced.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, field_validator

from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.forecast_metadata import ForecastMetadata
from solarops.forecast.domain.forecast_point import ForecastPoint
from solarops.shared_kernel import ForecastId, SiteId

__all__ = ["Forecast"]


class Forecast(BaseModel):
    """An ordered series of predicted points for one site and one kind."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    forecast_id: ForecastId
    site_id: SiteId
    kind: ForecastKind
    horizon_minutes: int
    points: tuple[ForecastPoint, ...]
    metadata: ForecastMetadata

    @field_validator("points")
    @classmethod
    def _points_must_be_ordered_and_nonempty(
        cls, value: tuple[ForecastPoint, ...]
    ) -> tuple[ForecastPoint, ...]:
        if not value:
            raise ValueError("Forecast.points must not be empty")
        for earlier, later in zip(value, value[1:], strict=False):
            if later.timestamp < earlier.timestamp:
                raise ValueError("Forecast.points must be ordered by timestamp")
        return value

    @property
    def generated_at(self) -> datetime:
        return self.metadata.generated_at

    def at_horizon(self, horizon_minutes: int) -> ForecastPoint:
        """The point closest to (without exceeding) the requested horizon.

        Used to read off the named evaluation checkpoints (15/30/60/360 min)
        from the full resolution-spaced series.
        """
        target = self.metadata.generated_at + timedelta(minutes=horizon_minutes)
        candidates = [p for p in self.points if p.timestamp <= target]
        if not candidates:
            return self.points[0]
        return candidates[-1]
