"""The FastAPI app (Phase 7a brief §1) — composition + wiring only, no
business logic. Builds one ``SystemComposition`` at startup (lifespan) and
hands it to routers via ``Depends(get_composition)``.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from solarops.api.dependencies import APISettings
from solarops.api.errors import register_exception_handlers
from solarops.api.routers import anomalies, approvals, commands, decisions, forecasts, ops, state
from solarops.observability.metrics import api_request_latency_seconds, api_requests_total
from solarops.platform.api_composition import build_system_composition

__all__ = ["app"]


class MetricsMiddleware(BaseHTTPMiddleware):
    """Doc 6 §11: request count + latency by route. Edge-layer instrumentation
    — no domain event backs this, it's a property of the HTTP layer itself.
    Uses the matched route *template* (``/sites/{site_id}/state``), not the
    raw path, so per-site-id values don't explode the label cardinality."""

    async def dispatch(self, request: Request, call_next):
        started_at = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - started_at

        route = request.scope.get("route")
        route_path = route.path if route is not None else request.url.path

        api_requests_total.labels(
            method=request.method, route=route_path, status=str(response.status_code)
        ).inc()
        api_request_latency_seconds.labels(method=request.method, route=route_path).observe(
            duration
        )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.composition = build_system_composition()
    yield


app = FastAPI(
    title="SolarOps AI",
    description="Thin API edge over the SolarOps AI control system (Doc 8 §10).",
    lifespan=lifespan,
)

app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=APISettings().cors_allowed_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)
register_exception_handlers(app)

app.include_router(state.router)
app.include_router(forecasts.router)
app.include_router(anomalies.router)
app.include_router(decisions.router)
app.include_router(commands.router)
app.include_router(approvals.router)
app.include_router(ops.router)
