"""Domain events the Anomaly context emits (Phase 6b brief §3)."""

from __future__ import annotations

from dataclasses import dataclass

from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.domain.severity import Severity
from solarops.shared_kernel import DomainEvent

__all__ = ["AnomalyDetected", "AlertRaised"]


@dataclass(frozen=True, slots=True, kw_only=True)
class AnomalyDetected(DomainEvent):
    """A new Anomaly was scored and persisted."""

    anomaly_type: AnomalyType
    severity: Severity
    confidence: float


@dataclass(frozen=True, slots=True, kw_only=True)
class AlertRaised(DomainEvent):
    """A detected Anomaly was published via ``AlertPublisher`` (Option A: detect-and-alert)."""

    anomaly_type: AnomalyType
    severity: Severity
