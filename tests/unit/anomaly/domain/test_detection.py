from datetime import UTC, datetime

import pytest

from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.domain.detection import Detection
from solarops.shared_kernel import AssetId

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_detection(**overrides) -> Detection:
    defaults = dict(
        anomaly_type=AnomalyType.BATTERY_OVERHEATING,
        confidence=0.9,
        affected_asset=AssetId("ASSET-battery-1"),
        evidence="battery_temp=50.0C > 45.0C",
        detector_name="rule-detector",
        detector_version="v1",
        detected_at=NOW,
    )
    defaults.update(overrides)
    return Detection(**defaults)


def test_constructs_with_valid_confidence():
    detection = make_detection()
    assert detection.confidence == 0.9


def test_rejects_confidence_below_zero():
    with pytest.raises(ValueError, match="confidence"):
        make_detection(confidence=-0.1)


def test_rejects_confidence_above_one():
    with pytest.raises(ValueError, match="confidence"):
        make_detection(confidence=1.1)


def test_is_immutable():
    detection = make_detection()
    with pytest.raises(Exception):
        detection.confidence = 0.5  # type: ignore[misc]
