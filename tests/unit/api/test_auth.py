"""Option A auth (brief §3): a key-lock on the three approval POSTs only —
reads and /decision-cycle stay open."""

from __future__ import annotations

from .conftest import ensure_pending_approval

SITE_ID = "site-001"


def _pending_approval_id(client) -> str:
    _command, approval_id = ensure_pending_approval(client)
    return approval_id


def test_approve_without_key_is_401(client):
    approval_id = _pending_approval_id(client)
    response = client.post(f"/approvals/{approval_id}/approve", json={"operator_id": "OP-1"})
    assert response.status_code == 401


def test_approve_with_wrong_key_is_401(client):
    approval_id = _pending_approval_id(client)
    response = client.post(
        f"/approvals/{approval_id}/approve",
        json={"operator_id": "OP-1"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


def test_reject_without_key_is_401(client):
    approval_id = _pending_approval_id(client)
    response = client.post(f"/approvals/{approval_id}/reject", json={"operator_id": "OP-1"})
    assert response.status_code == 401


def test_modify_without_key_is_401(client):
    approval_id = _pending_approval_id(client)
    response = client.post(
        f"/approvals/{approval_id}/modify",
        json={"operator_id": "OP-1", "modified_params": {}},
    )
    assert response.status_code == 401


def test_reads_and_decision_cycle_need_no_key(client):
    assert client.get(f"/sites/{SITE_ID}/state").status_code == 200
    assert client.get(f"/sites/{SITE_ID}/approvals/pending").status_code == 200
    assert client.post(f"/sites/{SITE_ID}/decision-cycle").status_code == 200
