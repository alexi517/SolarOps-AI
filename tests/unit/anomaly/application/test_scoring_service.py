from datetime import UTC, datetime

from solarops.anomaly.application.scoring_service import AnomalyScoringService
from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.domain.detection import Detection
from solarops.anomaly.infrastructure.config import AnomalyConfig
from solarops.anomaly.infrastructure.detector_registry import InMemoryDetectorRegistry
from solarops.anomaly.infrastructure.in_memory_anomaly_repository import (
    InMemoryAnomalyRepository,
)
from solarops.shared_kernel import AssetId, SiteId
from solarops.telemetry.domain.energy_state import EnergyState

from ...telemetry.domain.test_telemetry import make_telemetry

SITE_ID = SiteId("SITE-1")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)
ASSET = AssetId("ASSET-battery-1")
COVERS_BATTERY_OVERHEATING = frozenset({AnomalyType.BATTERY_OVERHEATING})


def make_state() -> EnergyState:
    telemetry = make_telemetry(site_id=SITE_ID, timestamp=NOW)
    return EnergyState.from_telemetry(telemetry, any_asset_offline=False)


class _FakeDetector:
    def __init__(self, name: str, detections: list[Detection]) -> None:
        self.name = name
        self.version = "v1"
        self._detections = detections

    def detect(self, state, history):  # noqa: ANN001, ANN201
        return list(self._detections)


def make_detection(confidence: float, detector_name: str) -> Detection:
    return Detection(
        anomaly_type=AnomalyType.BATTERY_OVERHEATING,
        confidence=confidence,
        affected_asset=ASSET,
        evidence=f"evidence from {detector_name}",
        detector_name=detector_name,
        detector_version="v1",
        detected_at=NOW,
    )


def make_service(registry: InMemoryDetectorRegistry, **config_overrides) -> AnomalyScoringService:
    config = AnomalyConfig(**config_overrides)
    return AnomalyScoringService(registry, InMemoryAnomalyRepository(), config)


def register_for_overheating(registry: InMemoryDetectorRegistry, detector) -> None:  # noqa: ANN001
    registry.register(detector, COVERS_BATTERY_OVERHEATING, {})


def test_no_active_detectors_produces_no_anomalies():
    registry = InMemoryDetectorRegistry()
    service = make_service(registry)
    anomalies, events = service.score(make_state(), [])
    assert anomalies == []
    assert events == []


def test_single_detection_becomes_one_anomaly():
    registry = InMemoryDetectorRegistry()
    register_for_overheating(registry, _FakeDetector("d1", [make_detection(0.95, "d1")]))
    service = make_service(registry, critical_confidence_threshold=0.85)

    anomalies, events = service.score(make_state(), [])

    assert len(anomalies) == 1
    assert anomalies[0].confidence == 0.95
    assert anomalies[0].supporting_evidence == ("[d1] evidence from d1",)
    assert len(events) == 1
    assert events[0].event_type == "AnomalyDetected"


def test_two_detectors_on_same_fault_merge_into_one_anomaly_with_max_confidence():
    registry = InMemoryDetectorRegistry()
    register_for_overheating(registry, _FakeDetector("d1", [make_detection(0.6, "d1")]))
    register_for_overheating(registry, _FakeDetector("d2", [make_detection(0.9, "d2")]))
    service = make_service(registry)

    anomalies, _events = service.score(make_state(), [])

    assert len(anomalies) == 1
    assert anomalies[0].confidence == 0.9
    assert len(anomalies[0].supporting_evidence) == 2


def test_severity_bucketing_uses_config_thresholds():
    registry = InMemoryDetectorRegistry()
    register_for_overheating(registry, _FakeDetector("d1", [make_detection(0.5, "d1")]))
    service = make_service(
        registry, warning_confidence_threshold=0.6, critical_confidence_threshold=0.9
    )

    anomalies, _events = service.score(make_state(), [])

    assert anomalies[0].severity.value == "INFO"


def test_anomaly_is_persisted_to_repository():
    registry = InMemoryDetectorRegistry()
    register_for_overheating(registry, _FakeDetector("d1", [make_detection(0.95, "d1")]))
    repository = InMemoryAnomalyRepository()
    service = AnomalyScoringService(registry, repository, AnomalyConfig())

    anomalies, _events = service.score(make_state(), [])

    assert repository.list_recent(SITE_ID, since=NOW) == anomalies


def test_detection_of_an_uncovered_type_is_dropped():
    # The detector fires BATTERY_OVERHEATING, but the registry only cleared it
    # for GRID_INSTABILITY — per-type gating (cleanup pass) must filter this out.
    registry = InMemoryDetectorRegistry()
    registry.register(
        _FakeDetector("d1", [make_detection(0.95, "d1")]),
        frozenset({AnomalyType.GRID_INSTABILITY}),
        {},
    )
    service = make_service(registry)

    anomalies, events = service.score(make_state(), [])

    assert anomalies == []
    assert events == []


def test_partially_covered_detector_only_reports_its_covered_type():
    registry = InMemoryDetectorRegistry()
    detections = [
        make_detection(0.9, "d1"),
        Detection(
            anomaly_type=AnomalyType.GRID_INSTABILITY,
            confidence=0.9,
            affected_asset=AssetId("ASSET-grid-1"),
            evidence="grid evidence",
            detector_name="d1",
            detector_version="v1",
            detected_at=NOW,
        ),
    ]
    registry.register(_FakeDetector("d1", detections), COVERS_BATTERY_OVERHEATING, {})
    service = make_service(registry)

    anomalies, _events = service.score(make_state(), [])

    assert len(anomalies) == 1
    assert anomalies[0].anomaly_type is AnomalyType.BATTERY_OVERHEATING
