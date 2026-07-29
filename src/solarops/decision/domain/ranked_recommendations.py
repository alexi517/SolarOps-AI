"""RankedRecommendations — an ordered list of Recommendations, best first (Phase 6c brief §4)."""

from __future__ import annotations

from dataclasses import dataclass

from solarops.decision.domain.recommendation import Recommendation

__all__ = ["RankedRecommendations"]


@dataclass(frozen=True, slots=True)
class RankedRecommendations:
    recommendations: tuple[Recommendation, ...]

    def __post_init__(self) -> None:
        if not self.recommendations:
            raise ValueError("RankedRecommendations must contain at least one Recommendation")

    @property
    def top(self) -> Recommendation:
        return self.recommendations[0]
