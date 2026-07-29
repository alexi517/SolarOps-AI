"""The walkthrough the Phase 7a brief's Definition of Done asks for: a real
command pauses awaiting approval, GET .../pending shows it, and each decision
(approve / reject / modify) drives it through the real Phase 5 pipeline."""

from __future__ import annotations

from .conftest import ensure_pending_approval

SITE_ID = "site-001"


def _start_pending_command(client) -> tuple[str, str]:
    command, approval_id = ensure_pending_approval(client)
    return command["command_id"], approval_id


def test_approve_completes_the_command_through_the_real_pipeline(client, auth_headers):
    command_id, approval_id = _start_pending_command(client)

    response = client.post(
        f"/approvals/{approval_id}/approve",
        json={"operator_id": "OP-demo", "reason": "looks safe"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "APPROVED"
    assert body["command"]["status"] == "COMPLETED"
    assert body["command"]["verification_result"]["passed"] is True
    assert body["command"]["execution_result"]["outcome"] == "SUCCESS"

    # No longer pending.
    pending_ids = [
        p["command_id"] for p in client.get(f"/sites/{SITE_ID}/approvals/pending").json()
    ]
    assert command_id not in pending_ids


def test_reject_terminates_the_command(client, auth_headers):
    command_id, approval_id = _start_pending_command(client)

    response = client.post(
        f"/approvals/{approval_id}/reject",
        json={"operator_id": "OP-demo", "reason": "not right now"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "REJECTED"
    assert body["command"]["status"] == "REJECTED_BY_OPERATOR"
    assert body["command"]["execution_result"] is None  # never dispatched

    detail = client.get(f"/commands/{command_id}").json()
    assert detail["status"] == "REJECTED_BY_OPERATOR"


def test_modify_records_the_operators_params_and_proceeds(client, auth_headers):
    _command_id, approval_id = _start_pending_command(client)

    response = client.post(
        f"/approvals/{approval_id}/modify",
        json={
            "operator_id": "OP-demo",
            "reason": "reduce the charge rate",
            "modified_params": {"power_kw": 10.0},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "MODIFIED"
    assert body["command"]["approval_decision"]["outcome"] == "MODIFIED"
    assert body["command"]["approval_decision"]["modified_params"] == {"power_kw": 10.0}
    # Proceeded through the real pipeline and completed — dispatched with the
    # command's original params, since Command has no method to retarget
    # itself from modified_params (see api/routers/approvals.py's docstring).
    assert body["command"]["status"] == "COMPLETED"


def test_deciding_an_already_decided_approval_is_409(client, auth_headers):
    _command_id, approval_id = _start_pending_command(client)
    first = client.post(
        f"/approvals/{approval_id}/approve",
        json={"operator_id": "OP-demo"},
        headers=auth_headers,
    )
    assert first.status_code == 200

    second = client.post(
        f"/approvals/{approval_id}/approve",
        json={"operator_id": "OP-demo"},
        headers=auth_headers,
    )
    assert second.status_code == 409


def test_unknown_approval_id_is_404(client, auth_headers):
    response = client.post(
        "/approvals/APR-does-not-exist/approve",
        json={"operator_id": "OP-demo"},
        headers=auth_headers,
    )
    assert response.status_code == 404
