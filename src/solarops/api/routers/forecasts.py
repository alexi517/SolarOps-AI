from __future__ import annotations

from fastapi import APIRouter, Depends

from solarops.api.dependencies import get_composition
from solarops.api.schemas.forecast import (
    ForecastAvailabilityResponse,
    ForecastResponse,
    SiteForecastsResponse,
)
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.platform.api_composition import SystemComposition
from solarops.shared_kernel import SiteId

router = APIRouter(tags=["forecasts"])


@router.get("/sites/{site_id}/forecasts", response_model=SiteForecastsResponse)
def get_forecasts(
    site_id: str, composition: SystemComposition = Depends(get_composition)
) -> SiteForecastsResponse:
    sid = SiteId(site_id)
    entries: list[ForecastAvailabilityResponse] = []
    for kind in ForecastKind:
        forecast = composition.forecast_repository.get_latest(sid, kind)
        if forecast is not None:
            entries.append(
                ForecastAvailabilityResponse(
                    kind=kind.value, available=True, forecast=ForecastResponse.from_domain(forecast)
                )
            )
        else:
            entries.append(
                ForecastAvailabilityResponse(
                    kind=kind.value,
                    available=False,
                    reason=(
                        "no model has passed the Document 6 evaluation gate for this "
                        "forecast kind yet (Phase 6a) — reported honestly, not faked"
                    ),
                )
            )
    return SiteForecastsResponse(site_id=site_id, forecasts=entries)
