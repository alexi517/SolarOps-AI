"""Domain events the Forecast context emits (Doc 8 §6.2)."""

from __future__ import annotations

from dataclasses import dataclass

from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.shared_kernel import DomainEvent

__all__ = ["ForecastGenerated"]


@dataclass(frozen=True, slots=True, kw_only=True)
class ForecastGenerated(DomainEvent):
    """A new Forecast was produced and persisted."""

    kind: ForecastKind
    model_name: str
    model_version: str
    horizon_minutes: int
