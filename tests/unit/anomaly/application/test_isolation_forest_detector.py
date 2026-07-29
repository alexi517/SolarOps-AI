import random
from datetime import UTC, datetime

import pytest

from solarops.anomaly.application.isolation_forest_detector import IsolationForestDetector
from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.infrastructure.config import AnomalyConfig
from solarops.shared_kernel import Power, SiteId, Temperature
from solarops.telemetry.domain.energy_state import EnergyState

from ...telemetry.domain.test_telemetry import make_telemetry

SITE_ID = SiteId("SITE-1")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_state(**overrides) -> EnergyState:
    telemetry = make_telemetry(site_id=SITE_ID, **overrides)
    return EnergyState.from_telemetry(telemetry, any_asset_offline=False)


def make_normal_history(n: int = 500) -> list[EnergyState]:
    # A numeric ``contamination`` (brief §4, config.py) needs a reasonably
    # large, representative training set to calibrate reliably — a handful
    # of near-constant readings makes the percentile estimate noisy.
    rng = random.Random(42)
    return [
        make_state(
            battery_temp=Temperature(28.0 + rng.uniform(-1.0, 1.0)),
            battery_power=Power(10.0 + rng.uniform(-1.0, 1.0)),
            solar_power=Power(80.0 + rng.uniform(-15.0, 15.0)),
            building_load=Power(58.0 + rng.uniform(-3.0, 3.0)),
        )
        for _ in range(n)
    ]


def test_fit_on_empty_history_raises():
    detector = IsolationForestDetector(AnomalyConfig())
    with pytest.raises(ValueError, match="empty"):
        detector.fit([])


def test_detect_before_fit_raises():
    detector = IsolationForestDetector(AnomalyConfig())
    with pytest.raises(RuntimeError, match="not been fitted"):
        detector.detect(make_state(), [])


def test_fit_then_detect_flags_outlier_battery_temp():
    detector = IsolationForestDetector(AnomalyConfig())
    result = detector.fit(make_normal_history())
    assert result.trained_on == 500
    assert detector.is_fitted is True

    outlier = make_state(battery_temp=Temperature(90.0))
    detections = detector.detect(outlier, [])
    assert len(detections) == 1
    assert detections[0].anomaly_type is AnomalyType.BATTERY_OVERHEATING


def test_no_detection_for_reading_within_normal_range():
    detector = IsolationForestDetector(AnomalyConfig())
    detector.fit(make_normal_history())

    typical = make_state(
        battery_temp=Temperature(28.5),
        battery_power=Power(10.2),
        solar_power=Power(80.0),
        building_load=Power(58.0),
    )
    detections = detector.detect(typical, [])
    assert detections == []


def test_carries_identity():
    detector = IsolationForestDetector(AnomalyConfig())
    assert detector.name == "isolation-forest-detector"
    assert detector.version == "v1"
