"""The one place that talks HTTP to the Phase 7a API (brief §3) — every page
goes through here, never calls httpx directly. No business logic: each
function is a single request, mapped straight from/to plain dicts."""

from __future__ import annotations

from typing import Any

import config
import httpx

__all__ = [
    "ApiError",
    "ApiUnreachable",
    "get_state",
    "get_forecasts",
    "get_anomalies",
    "get_recommendations",
    "run_decision_cycle",
    "list_commands",
    "get_command",
    "get_command_audit",
    "list_pending_approvals",
    "approve",
    "reject",
    "modify",
]

_client = httpx.Client(base_url=config.API_BASE_URL, timeout=config.REQUEST_TIMEOUT_SECONDS)


class ApiUnreachable(Exception):
    """The API could not be reached at all (connection refused, timed out)."""


class ApiError(Exception):
    """The API responded with a non-2xx status."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API error {status_code}: {detail}")


def _request(
    method: str, path: str, *, json: dict | None = None, headers: dict | None = None
) -> Any:
    try:
        response = _client.request(method, path, json=json, headers=headers)
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise ApiUnreachable(f"cannot reach the API at {config.API_BASE_URL}") from exc

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise ApiError(response.status_code, detail)

    return response.json()


def _auth_headers() -> dict[str, str]:
    return {"X-API-Key": config.API_KEY}


# --- State ---


def get_state(site_id: str) -> dict:
    return _request("GET", f"/sites/{site_id}/state")


# --- Forecasts ---


def get_forecasts(site_id: str) -> dict:
    return _request("GET", f"/sites/{site_id}/forecasts")


# --- Anomalies ---


def get_anomalies(site_id: str) -> list[dict]:
    return _request("GET", f"/sites/{site_id}/anomalies")


# --- Decisions ---


def get_recommendations(site_id: str) -> dict:
    return _request("GET", f"/sites/{site_id}/recommendations")


def run_decision_cycle(site_id: str) -> dict:
    return _request("POST", f"/sites/{site_id}/decision-cycle")


# --- Commands & audit ---


def list_commands(site_id: str) -> list[dict]:
    return _request("GET", f"/sites/{site_id}/commands")


def get_command(command_id: str) -> dict:
    return _request("GET", f"/commands/{command_id}")


def get_command_audit(command_id: str) -> list[dict]:
    return _request("GET", f"/commands/{command_id}/audit")


# --- Human approval ---


def list_pending_approvals(site_id: str) -> list[dict]:
    return _request("GET", f"/sites/{site_id}/approvals/pending")


def approve(approval_id: str, *, operator_id: str, reason: str = "") -> dict:
    body = {"operator_id": operator_id, "reason": reason}
    return _request(
        "POST", f"/approvals/{approval_id}/approve", json=body, headers=_auth_headers()
    )


def reject(approval_id: str, *, operator_id: str, reason: str = "") -> dict:
    body = {"operator_id": operator_id, "reason": reason}
    return _request(
        "POST", f"/approvals/{approval_id}/reject", json=body, headers=_auth_headers()
    )


def modify(
    approval_id: str, *, operator_id: str, reason: str, modified_params: dict
) -> dict:
    body = {"operator_id": operator_id, "reason": reason, "modified_params": modified_params}
    return _request(
        "POST", f"/approvals/{approval_id}/modify", json=body, headers=_auth_headers()
    )
