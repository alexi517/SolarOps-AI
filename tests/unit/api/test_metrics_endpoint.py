"""GET /metrics — Phase 7c brief §5: valid Prometheus output, and the
command-pipeline counters actually move when a command runs. Metrics are
global singletons (module-level prometheus_client objects) that persist
across the whole test session, so this asserts before/after deltas, never
an absolute count."""

from __future__ import annotations

import re

from .conftest import ensure_pending_approval

SITE_ID = "site-001"


def _metric_value(text: str, name: str) -> float:
    match = re.search(rf"^{re.escape(name)}(?:\{{[^}}]*\}})? ([0-9.eE+-]+)$", text, re.MULTILINE)
    assert match is not None, f"{name} not found in /metrics output"
    return float(match.group(1))


def test_metrics_returns_valid_prometheus_exposition_format(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")

    text = response.text
    assert "# HELP solarops_commands_issued_total" in text
    assert "# TYPE solarops_commands_issued_total counter" in text
    assert "solarops_commands_issued_total" in text


def test_decision_cycle_moves_the_issued_counter(client):
    before = client.get("/metrics").text
    issued_before = _metric_value(before, "solarops_commands_issued_total")

    response = client.post(f"/sites/{SITE_ID}/decision-cycle")
    assert response.status_code == 200

    after = client.get("/metrics").text
    issued_after = _metric_value(after, "solarops_commands_issued_total")
    assert issued_after == issued_before + 1


def test_a_pause_moves_the_approvals_required_counter(client):
    # Real conditions decide risk vs. confidence escalation (Phase 6d), so
    # retry across cycles for a guaranteed pause rather than assume any
    # single decision-cycle produces one.
    before = client.get("/metrics").text
    required_before = _metric_value(before, "solarops_approvals_required_total")

    ensure_pending_approval(client)

    after = client.get("/metrics").text
    required_after = _metric_value(after, "solarops_approvals_required_total")
    assert required_after >= required_before + 1


def test_approving_a_command_moves_the_completed_counter(client, auth_headers):
    _command, approval_id = ensure_pending_approval(client)

    before = client.get("/metrics").text
    completed_before = _metric_value(before, "solarops_commands_completed_total")
    approved_before = _metric_value(before, "solarops_approvals_approved_total")

    response = client.post(
        f"/approvals/{approval_id}/approve",
        json={"operator_id": "OP-metrics-test", "reason": "test"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["command"]["status"] == "COMPLETED"

    after = client.get("/metrics").text
    completed_after = _metric_value(after, "solarops_commands_completed_total")
    approved_after = _metric_value(after, "solarops_approvals_approved_total")

    assert completed_after == completed_before + 1
    assert approved_after == approved_before + 1


def test_api_request_metrics_use_the_route_template_not_the_raw_path(client):
    client.get(f"/sites/{SITE_ID}/state")
    text = client.get("/metrics").text
    assert 'route="/sites/{site_id}/state"' in text
    assert f'route="/sites/{SITE_ID}/state"' not in text
