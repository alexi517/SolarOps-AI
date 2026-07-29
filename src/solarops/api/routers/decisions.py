from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from solarops.api.dependencies import get_composition
from solarops.api.schemas.command import CommandSummaryResponse
from solarops.api.schemas.decision_cycle import DecisionCycleResponse
from solarops.api.schemas.recommendation import RankedRecommendationsResponse
from solarops.platform.api_composition import SystemComposition

router = APIRouter(tags=["decisions"])


@router.get("/sites/{site_id}/recommendations", response_model=RankedRecommendationsResponse)
def get_recommendations(
    site_id: str, composition: SystemComposition = Depends(get_composition)
) -> RankedRecommendationsResponse:
    context = composition.current_decision_context()
    if context is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no current state for site {site_id!r}")
    ranked = composition.recommend(context)
    return RankedRecommendationsResponse.from_domain(site_id, ranked)


@router.post("/sites/{site_id}/decision-cycle", response_model=DecisionCycleResponse)
def run_decision_cycle(
    site_id: str, composition: SystemComposition = Depends(get_composition)
) -> DecisionCycleResponse:
    ranked, command = composition.run_decision_cycle()
    return DecisionCycleResponse(
        site_id=site_id,
        recommendations=RankedRecommendationsResponse.from_domain(site_id, ranked),
        command=CommandSummaryResponse.from_domain(command),
    )
