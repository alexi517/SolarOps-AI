"""Headless golden-path verification (no browser available in this
environment): starts the real Phase 7a API — same SystemComposition-backed
app used in production — on a random local port, points api_client at it,
and runs each dashboard page through Streamlit's own script-running engine
(streamlit.testing.v1.AppTest), asserting nothing crashes and real data
renders. Includes one true end-to-end pass driven by actual widget clicks:
run a decision cycle -> see it pending -> approve it -> watch it complete —
the same walkthrough proven via raw HTTP in Phase 7a's tests, now via the UI.
"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import api_client
import httpx
import pytest
import uvicorn
from streamlit.testing.v1 import AppTest

REPO_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DIR = REPO_ROOT / "dashboard"


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest.fixture(scope="module")
def live_api(monkeypatch_module) -> Iterator[str]:
    from solarops.api.app import app as fastapi_app

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    config = uvicorn.Config(fastapi_app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)

    monkeypatch_module.setattr(
        api_client, "_client", httpx.Client(base_url=base_url, timeout=10.0)
    )

    yield base_url

    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="module")
def monkeypatch_module() -> Iterator[pytest.MonkeyPatch]:
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def _page(name: str) -> AppTest:
    return AppTest.from_file(str(DASHBOARD_DIR / "pages" / f"{name}.py"), default_timeout=30)


def _ensure_pending_via_dashboard(max_attempts: int = 30) -> AppTest:
    """Real, physically-simulated conditions decide whether a given decision
    cycle pauses (Phase 6d: via risk or confidence escalation), so click
    "Run decision cycle now" across attempts for one that does, rather than
    assume any single click produces a pending approval — mirrors
    tests/unit/api/conftest.py's ensure_pending_approval()."""
    for _ in range(max_attempts):
        recommendations = _page("recommendations")
        recommendations.run()
        recommendations.button[0].click().run()
        assert not recommendations.exception

        approvals = _page("approvals")
        approvals.run()
        assert not approvals.exception
        if any(b.label == "Approve" for b in approvals.button):
            return approvals
    raise AssertionError(f"no pending approval appeared after {max_attempts} attempts")


def test_overview_renders_the_current_state(live_api):
    at = _page("overview")
    at.run()
    assert not at.exception
    assert "Overview" in at.title[0].value
    assert any(m.label == "Battery SOC" for m in at.metric)
    # Themed Plotly charts: the battery gauge + solar-vs-load chart.
    assert len(at.get("plotly_chart")) == 2


def test_forecasts_shows_solar_and_marks_load_battery_unavailable(live_api):
    at = _page("forecasts")
    at.run()
    assert not at.exception
    subheaders = [s.value for s in at.subheader]
    assert subheaders == ["SOLAR_GENERATION", "BUILDING_LOAD", "BATTERY_SOC"]
    # Solar is registered -> one themed chart; load/battery-SOC are not ->
    # two designed "not yet available" placeholder cards (pill + reason caption).
    assert len(at.get("plotly_chart")) == 1
    markdown_text = " ".join(m.value for m in at.markdown)
    assert markdown_text.count("Not yet available") == 2
    captions = [c.value for c in at.caption]
    assert sum("evaluation gate" in text for text in captions) == 2


def test_anomalies_renders_without_error(live_api):
    at = _page("anomalies")
    at.run()
    assert not at.exception


def test_commands_starts_empty_and_says_so(live_api):
    # Runs before any decision-cycle test in this module — the live API's
    # command list is genuinely still empty at this point.
    at = _page("commands")
    at.run()
    assert not at.exception
    assert "Commands" in at.title[0].value
    assert any("No commands yet" in i.value for i in at.info)


def test_app_shell_loads_and_defaults_to_overview(live_api):
    at = AppTest.from_file(str(DASHBOARD_DIR / "app.py"), default_timeout=30)
    at.run()
    assert not at.exception
    assert "Overview" in at.title[0].value


def test_approve_a_command_end_to_end_through_the_dashboard(live_api):
    approvals = _ensure_pending_via_dashboard()

    approve_button = next(b for b in approvals.button if b.label == "Approve")
    approve_button.click().run()

    assert not approvals.exception
    # st.toast() — the "just happened" feedback (polish pass §3).
    assert any("COMPLETED" in t.value for t in approvals.toast)
    # The durable inline confirmation card (pill + command id), survives the
    # st.rerun() via session_state — see approvals.py's _record_result().
    assert any("COMPLETED" in m.value for m in approvals.markdown)


def test_reject_a_command_end_to_end_through_the_dashboard(live_api):
    approvals = _ensure_pending_via_dashboard()

    reject_button = next(b for b in approvals.button if b.label == "Reject")
    reject_button.click().run()

    assert not approvals.exception
    assert any("REJECTED_BY_OPERATOR" in t.value for t in approvals.toast)
    assert any("REJECTED_BY_OPERATOR" in m.value for m in approvals.markdown)
