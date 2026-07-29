"""GET /sites/{id}/recommendations, POST /sites/{id}/decision-cycle."""

from __future__ import annotations

SITE_ID = "site-001"


def test_get_recommendations_returns_ranked_list(client):
    response = client.get(f"/sites/{SITE_ID}/recommendations")
    assert response.status_code == 200
    body = response.json()
    assert body["site_id"] == SITE_ID
    assert len(body["recommendations"]) >= 1
    top = body["recommendations"][0]
    assert top["action"]
    assert 0.0 <= top["confidence"] <= 1.0


def test_decision_cycle_runs_the_top_recommendation_through_the_pipeline(client):
    response = client.post(f"/sites/{SITE_ID}/decision-cycle")
    assert response.status_code == 200
    body = response.json()
    assert body["site_id"] == SITE_ID
    assert len(body["recommendations"]["recommendations"]) >= 1

    command = body["command"]
    assert command["command_id"].startswith("CMD-")
    assert command["site_id"] == SITE_ID
    # It genuinely runs through the pipeline (real conditions decide risk
    # and confidence — Phase 6d — so the exact terminal status varies; the
    # approval-flow demo itself is proven deterministically in
    # test_approval_flow_end_to_end.py via ensure_pending_approval()).
    assert command["status"] in (
        "REJECTED_BY_POLICY",
        "BLOCKED_BY_SAFETY",
        "REJECTED_BY_RISK",
        "AWAITING_APPROVAL",
        "DISPATCH_FAILED",
        "EXECUTION_FAILED",
        "TIMED_OUT",
        "VERIFICATION_FAILED",
        "COMPLETED",
    )


def test_each_decision_cycle_produces_a_distinct_command(client):
    first = client.post(f"/sites/{SITE_ID}/decision-cycle").json()["command"]["command_id"]
    second = client.post(f"/sites/{SITE_ID}/decision-cycle").json()["command"]["command_id"]
    assert first != second
