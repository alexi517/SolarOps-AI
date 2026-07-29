"""Severity — coarse anomaly classification (Phase 6b brief §3).

The three-level scale itself is fixed domain vocabulary (mirrors
``shared_kernel.RiskLevel``'s pattern: a fixed enum, tunable *thresholds*
elsewhere — here, in ``AnomalyConfig``).
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["Severity"]


class Severity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
