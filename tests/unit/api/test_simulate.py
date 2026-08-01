"""POST /sites/{id}/simulate/fault — testing-only fault injection on the
live Digital Twin (e.g. force a grid outage on a running deployment)."""

from __future__ import annotations

SITE_ID = "site-001"


def test_inject_fault_without_key_is_401(client):
    response = client.post(
        f"/sites/{SITE_ID}/simulate/fault", json={"target": "grid", "fault": "OUTAGE"}
    )
    assert response.status_code == 401


def test_invalid_target_is_422(client, auth_headers):
    response = client.post(
        f"/sites/{SITE_ID}/simulate/fault",
        json={"target": "not-a-real-target", "fault": "OUTAGE"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_inject_and_clear_grid_outage_reflects_immediately(client, auth_headers):
    try:
        response = client.post(
            f"/sites/{SITE_ID}/simulate/fault",
            json={"target": "grid", "fault": "OUTAGE"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["target"] == "grid"
        assert body["fault"] == "OUTAGE"
        assert body["state"]["grid_status"] == "OUTAGE"

        # No extra decision-cycle click needed — the very next read already
        # reflects it, since the endpoint ticks + re-ingests immediately.
        state_response = client.get(f"/sites/{SITE_ID}/state")
        assert state_response.json()["grid_status"] == "OUTAGE"
    finally:
        # Always clear it, even if an assertion above failed — this client
        # is shared (session-scoped) across every other test file.
        clear_response = client.post(
            f"/sites/{SITE_ID}/simulate/fault",
            json={"target": "grid", "fault": None},
            headers=auth_headers,
        )
        assert clear_response.json()["state"]["grid_status"] == "CONNECTED"
