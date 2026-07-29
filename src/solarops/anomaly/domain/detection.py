"""Detection — VO: one detector's raw finding, before scoring/merging (Phase 6b brief §3).

Distinct from ``Anomaly``: a single detector run may fire several
``Detection``s for the same underlying fault (e.g. both the rule and
statistical detectors flag the same battery overheat) — ``scoring_service.py``
merges them into one ``Anomaly``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.shared_kernel import AssetId

__all__ = ["Detection"]


@dataclass(frozen=True, slots=True)
class Detection:
    anomaly_type: AnomalyType
    confidence: float
    affected_asset: AssetId
    evidence: str
    detector_name: str
    detector_version: str
    detected_at: datetime

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be within [0, 1], got {self.confidence}")
