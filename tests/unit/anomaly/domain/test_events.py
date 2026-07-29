from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.domain.events import AlertRaised, AnomalyDetected
from solarops.anomaly.domain.severity import Severity


def test_anomaly_detected_carries_classification():
    event = AnomalyDetected(
        aggregate_id="ANM-1",
        aggregate_type="Anomaly",
        anomaly_type=AnomalyType.GRID_INSTABILITY,
        severity=Severity.CRITICAL,
        confidence=1.0,
    )
    assert event.event_type == "AnomalyDetected"
    assert event.anomaly_type is AnomalyType.GRID_INSTABILITY


def test_alert_raised_carries_severity():
    event = AlertRaised(
        aggregate_id="ANM-1",
        aggregate_type="Anomaly",
        anomaly_type=AnomalyType.GRID_INSTABILITY,
        severity=Severity.WARNING,
    )
    assert event.event_type == "AlertRaised"
    assert event.severity is Severity.WARNING
