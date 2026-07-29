"""GET /sites/{id}/commands, GET /commands/{id}, GET /commands/{id}/audit."""

from __future__ import annotations

import pytest

from .conftest import ensure_pending_approval

SITE_ID = "site-001"


@pytest.fixture
def a_command(client) -> dict:
    return client.post(f"/sites/{SITE_ID}/decision-cycle").json()["command"]


def test_list_commands_includes_a_freshly_created_one(client, a_command):
    response = client.get(f"/sites/{SITE_ID}/commands")
    assert response.status_code == 200
    ids = [c["command_id"] for c in response.json()]
    assert a_command["command_id"] in ids


def test_get_command_detail_carries_gate_outcomes(client):
    # Needs a command that's actually still pending (to check
    # approval_decision/execution_result/verification_result are all still
    # None) — real conditions decide risk vs. confidence escalation (Phase
    # 6d), so retry across cycles rather than assume any single one pauses.
    command, _approval_id = ensure_pending_approval(client)
    response = client.get(f"/commands/{command['command_id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["command_id"] == command["command_id"]
    assert body["policy_result"]["passed"] is True
    assert body["safety_assessment"]["passed"] is True
    assert body["risk_assessment"]["level"] in ("LOW", "MEDIUM", "HIGH")
    assert body["approval_decision"] is None  # still pending
    assert body["execution_result"] is None
    assert body["verification_result"] is None


def test_get_command_detail_unknown_id_is_404(client):
    response = client.get("/commands/CMD-does-not-exist")
    assert response.status_code == 404


def test_get_command_audit_returns_the_trail_so_far(client, a_command):
    response = client.get(f"/commands/{a_command['command_id']}/audit")
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) >= 1
    assert all(entry["aggregate_id"] == a_command["command_id"] for entry in entries)


def test_get_command_audit_unknown_id_is_404(client):
    response = client.get("/commands/CMD-does-not-exist/audit")
    assert response.status_code == 404
