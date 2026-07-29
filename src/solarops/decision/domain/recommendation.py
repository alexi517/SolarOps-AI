"""Recommendation — aggregate root, the Decision context's published language (Doc 8 §6.3).

Crosses into the Control Plane as an immutable contract (§4: "A Recommendation
crosses the boundary as an immutable contract. Execution does not import
Decision's internals, and vice versa."). It expresses *what* to do and *why* —
never *how*; that's the Execution context's concern.

``params`` (Phase 5 addition) carries the actionable parameters Execution needs
to build a ``Command`` (e.g. ``power_kw``) — without it, Recommendation
expressed intent but not enough to act on it. Still just data crossing a
boundary, not a "how".

Phase 6c extends this with the Document 6 §8 explainability fields
(``why_now``, ``evidence``, ``alternatives``, ``risks`` — ``reason`` already
covers "why"). Additive only: ``CommandPlanner`` (Execution) reads only
``site_id``/``action``/``params``/``recommendation_id``, so existing consumers
are unaffected.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from solarops.decision.domain.confidence import ConfidenceBand
from solarops.shared_kernel import ActionType, RecommendationId, SiteId

__all__ = ["Recommendation"]


class Recommendation(BaseModel):
    """A single ranked, explainable suggestion — non-executable on its own."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    recommendation_id: RecommendationId
    site_id: SiteId
    action: ActionType
    params: dict = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)
    expected_benefit: str
    reason: str
    generated_at: datetime

    # --- Document 6 §8 explainability (Phase 6c) ---
    why_now: str = ""
    evidence: tuple[str, ...] = Field(default_factory=tuple)
    alternatives: tuple[str, ...] = Field(default_factory=tuple)
    risks: tuple[str, ...] = Field(default_factory=tuple)

    # --- Document 9 §8 confidence (Phase 6d) — band/factors alongside the
    # existing ``confidence`` score, additive. ---
    confidence_band: ConfidenceBand = ConfidenceBand.MEDIUM
    confidence_factors: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("generated_at")
    @classmethod
    def _generated_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Recommendation.generated_at must be timezone-aware")
        return value
