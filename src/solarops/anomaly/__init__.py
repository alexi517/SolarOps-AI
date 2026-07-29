"""Anomaly bounded context (Phase 6b brief) — new context, not yet in Doc 8's context map.

Reasons only about observed faults — never issues commands (brief §0). Six
anomaly types, three pluggable detectors (rule, statistical, Isolation
Forest) behind one interface; no detector configuration is registered unless
it passes the Document 6 §5 evaluation gate (§5). Detect-and-alert only
(Option A) — the `AlertPublisher` port is the seam a future Observability
context (or Decision, for Option B) would attach to.
"""
