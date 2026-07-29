"""The HTTP API (Doc 8 §10) — a thin FastAPI edge over the existing services.

Composition edge, like ``platform``/``workflow``: may import every bounded
context freely (Phase 7a brief §0). No bounded context may import ``api`` —
enforced by every import-linter contract's ``forbidden_modules``."""
