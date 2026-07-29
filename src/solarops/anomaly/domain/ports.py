"""Ports the Anomaly context depends on.

Defined in domain, implemented in infrastructure (Doc 8 §9.1). ``AnomalyDetector``
and ``TrainableDetector`` are the pluggable-detector interface (brief §0):
rule and statistical detectors implement ``AnomalyDetector`` only;
``IsolationForestDetector`` implements both.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol, runtime_checkable

from solarops.anomaly.domain.anomaly import Anomaly
from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.domain.detection import Detection
from solarops.shared_kernel import SiteId
from solarops.telemetry.domain.energy_state import EnergyState

__all__ = [
    "FitResult",
    "AnomalyDetector",
    "TrainableDetector",
    "AnomalyRepository",
    "AlertPublisher",
    "DetectorRegistry",
    "HistoricalDataSource",
    "LabeledReading",
    "FaultScenarioRun",
    "FaultScenarioSource",
]


@dataclass(frozen=True, slots=True)
class FitResult:
    """Outcome of ``TrainableDetector.fit`` — how much normal-operation data trained it."""

    trained_on: int
    trained_at: datetime


@runtime_checkable
class AnomalyDetector(Protocol):
    """The one interface every detector implements — rule-based, statistical, or ML.

    ``supported_types`` declares which ``AnomalyType``s this detector actually
    tries to catch — no single detector covers all six (that's the point of
    combining several, brief §4). ``AnomalyEvaluator`` only gates a detector
    against fault scenarios within its declared scope; a detector isn't
    penalised for not detecting something it never claimed to.
    """

    name: str
    version: str
    supported_types: frozenset[AnomalyType]

    def detect(self, state: EnergyState, history: list[EnergyState]) -> list[Detection]: ...


@runtime_checkable
class TrainableDetector(AnomalyDetector, Protocol):
    """An ``AnomalyDetector`` that can also be fit on normal-operation history."""

    def fit(self, normal_history: list[EnergyState]) -> FitResult: ...


class AnomalyRepository(Protocol):
    def save(self, anomaly: Anomaly) -> None: ...

    def list_recent(self, site_id: SiteId, *, since: datetime) -> list[Anomaly]: ...


class AlertPublisher(Protocol):
    """Where a detected, scored ``Anomaly`` goes (brief §6, Option A: detect-and-alert only).

    This is the disclosed seam: a real Observability context would implement
    this to fan out to logs/dashboards; Option B (feeding Decision) would be a
    second implementation or subscriber attached to the same ``AlertRaised``
    event stream — not built in 6b.
    """

    def publish(self, anomaly: Anomaly) -> None: ...


class DetectorRegistry(Protocol):
    """Tracks the currently-active (gate-passed) set of detectors, and — per the
    cleanup pass (docs/phase6b-cleanup-per-check-gating.md) — exactly which
    ``AnomalyType``s each one is cleared to report.

    ``ScoringService`` runs every detector ``get_active()`` returns, then
    keeps only the ``Detection``s whose type is in that detector's
    ``covered_types`` — this is what "combined by the scoring service"
    (brief §4) means concretely, now at per-type granularity: a detector
    covering four fault types but only passing the gate on three still goes
    active, just without the fourth. ``register`` is only ever called after a
    detector configuration has passed the evaluation gate (brief §5) for at
    least one type; the registry itself does not enforce that — the training
    service does.
    """

    def get_active(self) -> list[AnomalyDetector]: ...

    def covered_types(self, detector_name: str) -> frozenset[AnomalyType]: ...

    def register(
        self,
        detector: AnomalyDetector,
        covered_types: frozenset[AnomalyType],
        metrics_by_type: dict[AnomalyType, dict[str, float]],
    ) -> None: ...

    def get_metrics_by_type(self, detector_name: str) -> dict[AnomalyType, dict[str, float]]: ...


class HistoricalDataSource(Protocol):
    """Raw history a detector can train on. Implemented at the platform composition
    root by running the Digital Twin (brief §7) — Anomaly itself never imports
    Simulation."""

    def get_history(
        self, site_id: SiteId, *, as_of: datetime, lookback: timedelta
    ) -> list[EnergyState]: ...


@dataclass(frozen=True, slots=True)
class LabeledReading:
    """One tick of ground truth for evaluation: what happened, and whether it was anomalous."""

    state: EnergyState
    is_anomalous: bool
    expected_type: AnomalyType | None


@dataclass(frozen=True, slots=True)
class FaultScenarioRun:
    """One fault scenario's ground truth: a normal-operation prefix, then the fault."""

    scenario_name: str
    expected_type: AnomalyType
    readings: tuple[LabeledReading, ...]
    tick_seconds: float


class FaultScenarioSource(Protocol):
    """Runs the Document 6 §5 fault scenarios through the Digital Twin.

    Implemented at the platform composition root — spans Simulation and
    Anomaly, which is orchestration, neither context may import directly
    (brief §7/§1).
    """

    def scenario_names(self) -> list[str]: ...

    def run(self, scenario_name: str) -> FaultScenarioRun: ...
