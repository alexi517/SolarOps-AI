"""Domain events the Decision context emits (Doc 8 §6.3)."""

from __future__ import annotations

from dataclasses import dataclass

from solarops.shared_kernel import ActionType, DomainEvent

__all__ = ["RecommendationProduced"]


@dataclass(frozen=True, slots=True, kw_only=True)
class RecommendationProduced(DomainEvent):
    """A ``Recommendation`` was generated for a site."""

    action: ActionType
    confidence: float
