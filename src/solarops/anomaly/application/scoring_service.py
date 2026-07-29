"""AnomalyScoringService — runs active detectors, merges findings into Anomalys (brief §4).

Groups raw ``Detection``s from every currently-registered detector by
``(anomaly_type, affected_asset)`` — several detectors may fire on the same
underlying fault — takes the strongest confidence as the merged confidence,
buckets it into a ``Severity`` via ``AnomalyConfig``'s thresholds, and asks
``explanation.py`` for the ``recommended_action`` text. This is where the six
required ``Anomaly`` fields (brief §3) are populated.

Coverage is filtered per ``AnomalyType`` (cleanup pass,
docs/phase6b-cleanup-per-check-gating.md): a detector's ``detect()`` may
recognise a fault type it hasn't cleared the gate on (e.g. a rule detector
whose Battery Overheating check misses its recall target) — those
``Detection``s are dropped here before they ever become an ``Anomaly``, so
only gate-passed coverage ever reaches an alert.
"""

from __future__ import annotations

from solarops.anomaly.application.explanation import recommended_action_for
from solarops.anomaly.domain.anomaly import Anomaly
from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.domain.detection import Detection
from solarops.anomaly.domain.events import AnomalyDetected
from solarops.anomaly.domain.ports import AnomalyRepository, DetectorRegistry
from solarops.anomaly.domain.severity import Severity
from solarops.anomaly.infrastructure.config import AnomalyConfig
from solarops.shared_kernel import AnomalyId, AssetId, DomainEvent
from solarops.telemetry.domain.energy_state import EnergyState

__all__ = ["AnomalyScoringService"]


class AnomalyScoringService:
    def __init__(
        self,
        registry: DetectorRegistry,
        repository: AnomalyRepository,
        config: AnomalyConfig,
    ) -> None:
        self._registry = registry
        self._repository = repository
        self._config = config

    def score(
        self, state: EnergyState, history: list[EnergyState]
    ) -> tuple[list[Anomaly], list[DomainEvent]]:
        detections: list[Detection] = []
        for detector in self._registry.get_active():
            covered = self._registry.covered_types(detector.name)
            detections.extend(
                d for d in detector.detect(state, history) if d.anomaly_type in covered
            )

        grouped: dict[tuple[AnomalyType, AssetId], list[Detection]] = {}
        for detection in detections:
            key = (detection.anomaly_type, detection.affected_asset)
            grouped.setdefault(key, []).append(detection)

        anomalies: list[Anomaly] = []
        events: list[DomainEvent] = []
        for (anomaly_type, asset), group in grouped.items():
            confidence = max(d.confidence for d in group)
            evidence = tuple(f"[{d.detector_name}] {d.evidence}" for d in group)
            anomaly = Anomaly(
                anomaly_id=AnomalyId.generate(),
                site_id=state.site_id,
                detected_at=state.timestamp,
                anomaly_type=anomaly_type,
                severity=self._severity_for(confidence),
                confidence=confidence,
                affected_asset=asset,
                supporting_evidence=evidence,
                recommended_action=recommended_action_for(anomaly_type),
            )
            self._repository.save(anomaly)
            anomalies.append(anomaly)
            events.append(
                AnomalyDetected(
                    aggregate_id=str(anomaly.anomaly_id),
                    aggregate_type="Anomaly",
                    anomaly_type=anomaly_type,
                    severity=anomaly.severity,
                    confidence=confidence,
                )
            )

        return anomalies, events

    def _severity_for(self, confidence: float) -> Severity:
        if confidence >= self._config.critical_confidence_threshold:
            return Severity.CRITICAL
        if confidence >= self._config.warning_confidence_threshold:
            return Severity.WARNING
        return Severity.INFO
