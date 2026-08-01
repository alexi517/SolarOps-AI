"""Convenience runner for the Phase 7a API. Once it's up, browse
http://127.0.0.1:8000/docs locally, or http://<this machine's IP>:8000/docs
from another machine (e.g. a remote VM's public IP).

Binds 0.0.0.0 so it's reachable from other machines, not just itself —
harmless for purely local use, since 127.0.0.1/localhost still resolves to
the same server either way.
"""

from __future__ import annotations

import uvicorn

if __name__ == "__main__":
    uvicorn.run("solarops.api.app:app", host="0.0.0.0", port=8000, reload=False)
