from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends

from solarops.api.dependencies import get_composition
from solarops.api.schemas.anomaly import AnomalyResponse
from solarops.platform.api_composition import SystemComposition
from solarops.shared_kernel import SiteId

router = APIRouter(tags=["anomalies"])

_RECENT_WINDOW = timedelta(hours=24)


@router.get("/sites/{site_id}/anomalies", response_model=list[AnomalyResponse])
def get_anomalies(
    site_id: str, composition: SystemComposition = Depends(get_composition)
) -> list[AnomalyResponse]:
    sid = SiteId(site_id)
    since = composition.clock.now() - _RECENT_WINDOW
    anomalies = composition.anomaly_repository.list_recent(sid, since=since)
    return [AnomalyResponse.from_domain(a) for a in anomalies]
