"""One TestClient (and one SystemComposition, built via the app's lifespan)
shared across the whole api test session — building it trains the real
Forecast/Anomaly gates (6a/6b), which costs a few seconds; nothing under test
here mutates shared state in a way that makes cross-file ordering matter
(each decision-cycle produces its own fresh Command)."""

from __future__ import annotations

import dataclasses
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


def ensure_pending_approval(client: TestClient, *, max_attempts: int = 5) -> tuple[dict, str]:
    """Run decision cycles until one pauses for approval.

    Which risk level a real decision cycle produces depends on genuinely
    simulated physics (solar/load/battery state) — retrying a bounded number
    of cycles and hoping one happens to land on HIGH risk turned out not to
    be reliable: under calm, moderate conditions (a common real state) risk
    stays LOW for as long as those conditions hold, no matter how many times
    you retry a call that barely advances simulated time.

    Instead, this forces the site's Policy into maintenance mode *with* an
    override (so the Policy gate still permits every action type — only
    ``maintenance_override=False`` would restrict CHARGE_BATTERY) for the
    duration of the call. ``RiskAssessor`` treats ``policy.maintenance_mode``
    as an unconditional HIGH-risk factor (safety/application/risk_assessor.py)
    regardless of the action or its magnitude, which makes reaching
    AWAITING_APPROVAL deterministic rather than time-of-day-dependent. The
    original policy is always restored afterwards, since the composition is
    shared across the whole test session.
    """
    composition = client.app.state.composition
    original_policy = composition.policy_repository.get_current(composition.site_id)
    forced_policy = dataclasses.replace(
        original_policy, maintenance_mode=True, maintenance_override=True
    )
    composition.policy_repository.save(forced_policy)
    try:
        for _ in range(max_attempts):
            command = client.post(f"/sites/{SITE_ID}/decision-cycle").json()["command"]
            if command["status"] != "AWAITING_APPROVAL":
                continue
            pending = client.get(f"/sites/{SITE_ID}/approvals/pending").json()
            match = next((p for p in pending if p["command_id"] == command["command_id"]), None)
            if match is not None:
                return command, match["approval_request_id"]
        raise AssertionError(f"no pending approval appeared after {max_attempts} decision cycles")
    finally:
        composition.policy_repository.save(original_policy)
