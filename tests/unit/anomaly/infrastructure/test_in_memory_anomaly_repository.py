from datetime import UTC, datetime, timedelta

from solarops.anomaly.domain.anomaly import Anomaly
from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.domain.severity import Severity
from solarops.anomaly.infrastructure.in_memory_anomaly_repository import (
    InMemoryAnomalyRepository,
)
from solarops.shared_kernel import AnomalyId, AssetId, SiteId

SITE_ID = SiteId("SITE-1")
OTHER_SITE = SiteId("SITE-2")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_anomaly(site_id: SiteId = SITE_ID, detected_at: datetime = NOW) -> Anomaly:
    return Anomaly(
        anomaly_id=AnomalyId.generate(),
        site_id=site_id,
        detected_at=detected_at,
        anomaly_type=AnomalyType.BATTERY_OVERHEATING,
        severity=Severity.CRITICAL,
        confidence=0.9,
        affected_asset=AssetId("ASSET-battery-1"),
        supporting_evidence=("evidence",),
        recommended_action="act now",
    )


def test_list_recent_is_empty_before_save():
    repository = InMemoryAnomalyRepository()
    assert repository.list_recent(SITE_ID, since=NOW - timedelta(hours=1)) == []


def test_save_then_list_recent_round_trips():
    repository = InMemoryAnomalyRepository()
    anomaly = make_anomaly()
    repository.save(anomaly)
    assert repository.list_recent(SITE_ID, since=NOW - timedelta(hours=1)) == [anomaly]


def test_list_recent_excludes_older_than_since():
    repository = InMemoryAnomalyRepository()
    repository.save(make_anomaly(detected_at=NOW - timedelta(hours=2)))
    assert repository.list_recent(SITE_ID, since=NOW - timedelta(hours=1)) == []


def test_list_recent_scoped_per_site():
    repository = InMemoryAnomalyRepository()
    repository.save(make_anomaly(site_id=OTHER_SITE))
    assert repository.list_recent(SITE_ID, since=NOW - timedelta(hours=1)) == []
