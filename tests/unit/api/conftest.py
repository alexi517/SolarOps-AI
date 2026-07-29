"""One TestClient (and one SystemComposition, built via the app's lifespan)
shared across the whole api test session — building it trains the real
Forecast/Anomaly gates (6a/6b), which costs a few seconds; nothing under test
here mutates shared state in a way that makes cross-file ordering matter
(each decision-cycle produces its own fresh Command)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from solarops.api.app import app

VALID_API_KEY = "solarops-demo-key"
SITE_ID = "site-001"


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"X-API-Key": VALID_API_KEY}


def ensure_pending_approval(client: TestClient, *, max_attempts: int = 30) -> tuple[dict, str]:
    """Run decision cycles until one pauses for approval.

    Phase 6d made this a genuine function of real, physically-simulated
    conditions (risk level *or* confidence band — see
    platform/api_composition.py) rather than a scripted certainty, so tests
    that need a pending approval to act on retry across a bounded number of
    cycles instead of assuming any single call produces one. Each call also
    ticks telemetry forward, so successive attempts see slightly different
    conditions, not a frozen retry of the exact same input.
    """
    for _ in range(max_attempts):
        command = client.post(f"/sites/{SITE_ID}/decision-cycle").json()["command"]
        if command["status"] != "AWAITING_APPROVAL":
            continue
        pending = client.get(f"/sites/{SITE_ID}/approvals/pending").json()
        match = next((p for p in pending if p["command_id"] == command["command_id"]), None)
        if match is not None:
            return command, match["approval_request_id"]
    raise AssertionError(f"no pending approval appeared after {max_attempts} decision cycles")
