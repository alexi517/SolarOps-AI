"""Testing-only simulation control — inject or clear a fault on the running
Digital Twin (e.g. force a grid outage) so a scenario can be exercised
against a live deployment, not just a local script. Behind the same
X-API-Key check as the other mutating endpoints (brief §3) since this can
change what the system believes is happening at the site.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from solarops.api.dependencies import get_composition, require_api_key
from solarops.api.schemas.simulate import FaultInjectionRequest, FaultInjectionResponse
from solarops.api.schemas.state import EnergyStateResponse
from solarops.platform.api_composition import SystemComposition

router = APIRouter(tags=["simulate"])


@router.post(
    "/sites/{site_id}/simulate/fault",
    response_model=FaultInjectionResponse,
    dependencies=[Depends(require_api_key)],
)
def inject_fault(
    site_id: str,
    body: FaultInjectionRequest,
    composition: SystemComposition = Depends(get_composition),
) -> FaultInjectionResponse:
    composition.twin.inject_fault(body.target, body.fault)
    # Tick + re-ingest immediately, rather than waiting for the next manual
    # decision cycle — the whole point of this endpoint is to see the effect
    # show up right away, not on some later click.
    state = composition.refresh_telemetry()
    return FaultInjectionResponse(
        target=body.target,
        fault=body.fault,
        state=EnergyStateResponse.from_domain(state),
    )
