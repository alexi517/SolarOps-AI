from datetime import UTC, datetime

from solarops.anomaly.domain.anomaly import Anomaly
from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.domain.severity import Severity
from solarops.anomaly.infrastructure.in_memory_alert_publisher import InMemoryAlertPublisher
from solarops.shared_kernel import AnomalyId, AssetId, SiteId

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_anomaly() -> Anomaly:
    return Anomaly(
        anomaly_id=AnomalyId.generate(),
        site_id=SiteId("SITE-1"),
        detected_at=NOW,
        anomaly_type=AnomalyType.GRID_INSTABILITY,
        severity=Severity.WARNING,
        confidence=0.7,
        affected_asset=AssetId("ASSET-grid-1"),
        supporting_evidence=("evidence",),
        recommended_action="act",
    )


def test_publish_records_the_anomaly():
    publisher = InMemoryAlertPublisher()
    anomaly = make_anomaly()
    publisher.publish(anomaly)
    assert publisher.published == [anomaly]


def test_publish_accumulates_across_calls():
    publisher = InMemoryAlertPublisher()
    publisher.publish(make_anomaly())
    publisher.publish(make_anomaly())
    assert len(publisher.published) == 2
