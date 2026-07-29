from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from solarops.api.dependencies import get_composition
from solarops.api.schemas.state import EnergyStateResponse
from solarops.platform.api_composition import SystemComposition
from solarops.shared_kernel import SiteId

router = APIRouter(tags=["state"])


@router.get("/sites/{site_id}/state", response_model=EnergyStateResponse)
def get_state(
    site_id: str, composition: SystemComposition = Depends(get_composition)
) -> EnergyStateResponse:
    state = composition.state_manager.get_current(SiteId(site_id))
    if state is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no current state for site {site_id!r}")
    return EnergyStateResponse.from_domain(state)
