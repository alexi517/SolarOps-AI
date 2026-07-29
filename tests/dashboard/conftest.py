"""dashboard/ sits outside src/solarops/ and uses bare top-level imports
(`import config`, `from api_client import ...`) — exactly what Streamlit
puts on sys.path when it runs `dashboard/app.py` directly. Reproduce that
here before anything under dashboard/ gets imported."""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import pytest

DASHBOARD_DIR = Path(__file__).resolve().parents[2] / "dashboard"
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

import api_client  # noqa: E402


@pytest.fixture
def mock_api(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[[Callable], httpx.Client]]:
    installed: list[httpx.Client] = []

    def _install(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
        client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://testserver")
        monkeypatch.setattr(api_client, "_client", client)
        installed.append(client)
        return client

    yield _install

    for client in installed:
        client.close()
