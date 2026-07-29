"""CommandPlan — the planner's output (Doc 8 §6.5), before a Command aggregate exists."""

from __future__ import annotations

from dataclasses import dataclass, field

from solarops.shared_kernel import ActionType, AssetId, RecommendationId, SiteId

__all__ = ["CommandPlan"]


@dataclass(frozen=True, slots=True)
class CommandPlan:
    recommendation_id: RecommendationId
    site_id: SiteId
    asset_id: AssetId
    action: ActionType
    params: dict = field(default_factory=dict)
    idempotency_key: str = ""
