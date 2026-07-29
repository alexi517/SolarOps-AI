"""DI: hand routers the wired services from the composition built once at
startup (Phase 7a brief §1), plus Option A auth (brief §3).
"""

from __future__ import annotations

from fastapi import Header, HTTPException, Request, status
from pydantic_settings import BaseSettings, SettingsConfigDict

from solarops.platform.api_composition import SystemComposition

__all__ = ["get_composition", "require_api_key", "APISettings"]


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SOLAROPS_", env_file=".env", extra="ignore")

    api_key: str = "solarops-demo-key"


def get_composition(request: Request) -> SystemComposition:
    return request.app.state.composition


# TODO(auth-rbac): CESF §16 — this is a minimal demo-grade shared-secret check
# on the three mutating approval endpoints only (Option A, brief §3). Replace
# with real authenticated, role-based authorisation before this leaves demo use;
# read endpoints and /decision-cycle stay open per the brief.
def require_api_key(x_api_key: str = Header(default="")) -> None:
    settings = APISettings()
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing or invalid X-API-Key"
        )
