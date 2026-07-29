"""Liveness + the real Prometheus exposition (Phase 7c brief §2). Every
metric definition lives in ``observability/metrics.py``; this route just
refreshes the on-scrape gauge (registered model versions) and renders
whatever's currently in the registry — works with no Docker running, since
it's plain in-process state (brief §4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from solarops.api.dependencies import get_composition
from solarops.platform.api_composition import SystemComposition

router = APIRouter(tags=["ops"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(composition: SystemComposition = Depends(get_composition)) -> PlainTextResponse:
    composition.refresh_model_version_gauges()
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
