"""Recommendation / RankedRecommendations -> JSON."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from solarops.decision.domain.ranked_recommendations import RankedRecommendations
from solarops.decision.domain.recommendation import Recommendation

__all__ = ["RecommendationResponse", "RankedRecommendationsResponse"]


class RecommendationResponse(BaseModel):
    recommendation_id: str
    site_id: str
    action: str
    params: dict
    confidence: float
    expected_benefit: str
    reason: str
    generated_at: datetime
    why_now: str
    evidence: list[str]
    alternatives: list[str]
    risks: list[str]

    @classmethod
    def from_domain(cls, recommendation: Recommendation) -> RecommendationResponse:
        return cls(
            recommendation_id=str(recommendation.recommendation_id),
            site_id=str(recommendation.site_id),
            action=recommendation.action.value,
            params=dict(recommendation.params),
            confidence=recommendation.confidence,
            expected_benefit=recommendation.expected_benefit,
            reason=recommendation.reason,
            generated_at=recommendation.generated_at,
            why_now=recommendation.why_now,
            evidence=list(recommendation.evidence),
            alternatives=list(recommendation.alternatives),
            risks=list(recommendation.risks),
        )


class RankedRecommendationsResponse(BaseModel):
    site_id: str
    recommendations: list[RecommendationResponse]

    @classmethod
    def from_domain(
        cls, site_id: str, ranked: RankedRecommendations
    ) -> RankedRecommendationsResponse:
        return cls(
            site_id=site_id,
            recommendations=[
                RecommendationResponse.from_domain(r) for r in ranked.recommendations
            ],
        )
