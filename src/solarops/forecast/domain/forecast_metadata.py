"""ForecastMetadata — VO: provenance of one Forecast (Doc 8 §6.2).

Every forecast carries the model that produced it, so it is explainable and
observable by construction (Phase 6a brief §0) — no downstream consumer ever
has to guess which model version made a prediction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

__all__ = ["ForecastMetadata"]


@dataclass(frozen=True, slots=True)
class ForecastMetadata:
    model_name: str
    model_version: str
    generated_at: datetime
    horizon_minutes: int
    resolution_minutes: int
    confidence: float | None = None

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be within [0, 1], got {self.confidence}")
        if self.horizon_minutes <= 0:
            raise ValueError(f"horizon_minutes must be positive, got {self.horizon_minutes}")
        if self.resolution_minutes <= 0:
            raise ValueError(f"resolution_minutes must be positive, got {self.resolution_minutes}")
