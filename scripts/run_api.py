"""Convenience runner for the Phase 7a API. Browse http://0.0.0.0:8000/docs
once it's up for the automatic OpenAPI page."""

from __future__ import annotations

import uvicorn

if __name__ == "__main__":
    uvicorn.run("solarops.api.app:app", host="127.0.0.1", port=8000, reload=False)
