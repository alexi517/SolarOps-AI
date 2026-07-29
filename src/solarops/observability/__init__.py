"""Prometheus metrics (Doc 8 §10; Phase 7c brief) — a leaf edge package like
``api``/``platform``/``workflow``: it imports nothing from any bounded
context, and every context's import-linter contract already forbids
depending on it. See ``metrics.py`` for the metric definitions."""
