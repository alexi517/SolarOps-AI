"""Forecast bounded context (Document 8 §6.2) — Supporting.

Reasons only about the future — never issues commands (Doc 8 §0 principles,
Phase 6a brief §0). Three predictors (Solar Generation, Building Load, Battery
SOC) share one swappable ``ForecastModel`` interface; no model is registered
unless it passes the Document 6 evaluation gate (§6). Decision (Phase 6c) is
the customer.
"""
