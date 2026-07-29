"""Dashboard configuration — API base URL and key come from the environment,
never hardcoded in a page (Phase 7b brief §3). Defaults match the API's own
demo defaults (solarops/api/dependencies.py) so both work out of the box."""

from __future__ import annotations

import os

API_BASE_URL = os.environ.get("SOLAROPS_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_KEY = os.environ.get("SOLAROPS_API_KEY", "solarops-demo-key")
SITE_ID = os.environ.get("SOLAROPS_SITE_ID", "site-001")
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("SOLAROPS_API_TIMEOUT_SECONDS", "10"))
