"""api_client.py is the one place that talks HTTP to the API — these tests
mock the transport (httpx.MockTransport), so no live server is needed."""

from __future__ import annotations

import api_client
import config
import httpx
import pytest


def test_get_state_parses_the_response_body(mock_api):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/sites/site-001/state"
        return httpx.Response(200, json={"site_id": "site-001", "battery_soc_pct": 50.0})

    mock_api(handler)
    result = api_client.get_state("site-001")
    assert result["battery_soc_pct"] == 50.0


def test_non_2xx_raises_api_error_with_the_fastapi_detail_message(mock_api):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "no current state for site 'x'"})

    mock_api(handler)
    with pytest.raises(api_client.ApiError) as exc_info:
        api_client.get_state("x")
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "no current state for site 'x'"


def test_connection_failure_raises_api_unreachable(mock_api):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    mock_api(handler)
    with pytest.raises(api_client.ApiUnreachable):
        api_client.get_state("site-001")


def test_timeout_raises_api_unreachable(mock_api):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    mock_api(handler)
    with pytest.raises(api_client.ApiUnreachable):
        api_client.get_state("site-001")


def test_approve_sends_the_api_key_header_and_body(mock_api):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["api_key"] = request.headers.get("x-api-key")
        seen["body"] = request.content
        return httpx.Response(200, json={"command": {"command_id": "CMD-1", "status": "COMPLETED"}})

    mock_api(handler)
    result = api_client.approve("APR-1", operator_id="OP-1", reason="fine")

    assert seen["path"] == "/approvals/APR-1/approve"
    assert seen["api_key"] == config.API_KEY
    assert b"OP-1" in seen["body"]
    assert result["command"]["status"] == "COMPLETED"


def test_reject_and_modify_also_send_the_api_key_header(mock_api):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers.get("x-api-key"))
        command = {"command_id": "CMD-1", "status": "REJECTED_BY_OPERATOR"}
        return httpx.Response(200, json={"command": command})

    mock_api(handler)
    api_client.reject("APR-1", operator_id="OP-1", reason="no")
    api_client.modify(
        "APR-1", operator_id="OP-1", reason="tweak", modified_params={"power_kw": 5.0}
    )

    assert seen == [config.API_KEY, config.API_KEY]


def test_gets_do_not_send_the_api_key_header(mock_api):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["api_key"] = request.headers.get("x-api-key")
        return httpx.Response(200, json=[])

    mock_api(handler)
    api_client.list_pending_approvals("site-001")
    assert seen["api_key"] is None


def test_decision_cycle_is_a_post(mock_api):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/sites/site-001/decision-cycle"
        return httpx.Response(200, json={"site_id": "site-001", "command": {}})

    mock_api(handler)
    api_client.run_decision_cycle("site-001")
