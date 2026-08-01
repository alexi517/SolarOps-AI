"""Convenience runner for the Phase 7a API. Browse http://127.0.0.1:8000/docs
once it's up for the automatic OpenAPI page.

Binds 0.0.0.0 so it's reachable from other machines (e.g. a browser hitting
a remote VM's public IP), not just localhost — harmless for purely local use,
since 127.0.0.1/localhost still resolves to the same server either way.
"""

from __future__ import annotations

import uvicorn

if __name__ == "__main__":
    uvicorn.run("solarops.api.app:app", host="0.0.0.0", port=8000, reload=False)
