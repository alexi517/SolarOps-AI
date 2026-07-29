from datetime import UTC, datetime

import pytest

from solarops.anomaly.domain.anomaly import Anomaly
from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.domain.severity import Severity
from solarops.shared_kernel import AnomalyId, AssetId, SiteId

SITE_ID = SiteId("SITE-1")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_anomaly(**overrides) -> Anomaly:
    defaults = dict(
        anomaly_id=AnomalyId.generate(),
        site_id=SITE_ID,
        detected_at=NOW,
        anomaly_type=AnomalyType.BATTERY_OVERHEATING,
        severity=Severity.CRITICAL,
        confidence=0.95,
        affected_asset=AssetId("ASSET-battery-1"),
        supporting_evidence=("[rule-detector] battery_temp=50.0C > 45.0C",),
        recommended_action="Reduce battery charge/discharge current immediately.",
    )
    defaults.update(overrides)
    return Anomaly(**defaults)


def test_carries_all_six_required_fields():
    anomaly = make_anomaly()
    assert anomaly.anomaly_type is AnomalyType.BATTERY_OVERHEATING
    assert anomaly.severity is Severity.CRITICAL
    assert anomaly.confidence == 0.95
    assert anomaly.affected_asset == AssetId("ASSET-battery-1")
    assert anomaly.supporting_evidence == ("[rule-detector] battery_temp=50.0C > 45.0C",)
    assert anomaly.recommended_action


def test_rejects_naive_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        make_anomaly(detected_at=datetime(2026, 7, 27, 12, 0))


def test_rejects_empty_evidence():
    with pytest.raises(ValueError, match="supporting_evidence"):
        make_anomaly(supporting_evidence=())


def test_rejects_confidence_outside_unit_interval():
    with pytest.raises(ValueError):
        make_anomaly(confidence=1.5)


def test_is_immutable():
    anomaly = make_anomaly()
    with pytest.raises(Exception):
        anomaly.severity = Severity.INFO  # type: ignore[misc]
