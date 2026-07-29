"""GET /sites/{id}/state, /forecasts, /anomalies, /health, /metrics, /docs."""

from __future__ import annotations

SITE_ID = "site-001"


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_state_returns_the_current_reading(client):
    response = client.get(f"/sites/{SITE_ID}/state")
    assert response.status_code == 200
    body = response.json()
    assert body["site_id"] == SITE_ID
    assert isinstance(body["solar_power_kw"], float)
    assert isinstance(body["battery_soc_pct"], float)


def test_get_state_unknown_site_is_404(client):
    response = client.get("/sites/no-such-site/state")
    assert response.status_code == 404


def test_get_forecasts_reflects_solar_registered_load_and_battery_unavailable(client):
    response = client.get(f"/sites/{SITE_ID}/forecasts")
    assert response.status_code == 200
    forecasts = {entry["kind"]: entry for entry in response.json()["forecasts"]}

    assert forecasts["SOLAR_GENERATION"]["available"] is True
    assert forecasts["SOLAR_GENERATION"]["forecast"] is not None

    assert forecasts["BUILDING_LOAD"]["available"] is False
    assert forecasts["BUILDING_LOAD"]["forecast"] is None
    assert forecasts["BUILDING_LOAD"]["reason"]

    assert forecasts["BATTERY_SOC"]["available"] is False
    assert forecasts["BATTERY_SOC"]["forecast"] is None


def test_get_anomalies_returns_a_list(client):
    response = client.get(f"/sites/{SITE_ID}/anomalies")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_metrics_is_prometheus_plain_text(client):
    # Full coverage of the real metric set lives in test_metrics_endpoint.py
    # (Phase 7c) — this just confirms the route still serves valid exposition
    # format, the original intent of this test from Phase 7a's stub.
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "solarops_commands_issued_total" in response.text


def test_openapi_docs_render(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/sites/{site_id}/state" in paths
    assert "/approvals/{approval_id}/approve" in paths

    docs_response = client.get("/docs")
    assert docs_response.status_code == 200
