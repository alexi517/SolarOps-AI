from datetime import UTC, datetime

import pytest

from solarops.decision.domain.ranked_recommendations import RankedRecommendations
from solarops.decision.domain.recommendation import Recommendation
from solarops.shared_kernel import ActionType, RecommendationId, SiteId

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_recommendation(action: ActionType) -> Recommendation:
    return Recommendation(
        recommendation_id=RecommendationId.generate(),
        site_id=SiteId("SITE-1"),
        action=action,
        confidence=0.8,
        expected_benefit="x",
        reason="x",
        generated_at=NOW,
    )


def test_top_returns_the_first_recommendation():
    first = make_recommendation(ActionType.CHARGE_BATTERY)
    second = make_recommendation(ActionType.HOLD_BATTERY)
    ranked = RankedRecommendations(recommendations=(first, second))
    assert ranked.top is first


def test_rejects_empty_recommendations():
    with pytest.raises(ValueError, match="at least one"):
        RankedRecommendations(recommendations=())
