"""Response for POST /sites/{site_id}/decision-cycle — recommendations plus
the resulting command, since the cycle also runs the top recommendation
through the real Phase 5 pipeline (see platform/api_composition.py)."""

from __future__ import annotations

from pydantic import BaseModel

from .command import CommandSummaryResponse
from .recommendation import RankedRecommendationsResponse

__all__ = ["DecisionCycleResponse"]


class DecisionCycleResponse(BaseModel):
    site_id: str
    recommendations: RankedRecommendationsResponse
    command: CommandSummaryResponse
