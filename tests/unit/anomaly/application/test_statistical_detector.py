from datetime import UTC, datetime

from solarops.anomaly.application.statistical_detector import StatisticalDetector
from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.infrastructure.config import AnomalyConfig
from solarops.shared_kernel import Power, SiteId
from solarops.telemetry.domain.energy_state import EnergyState

from ...telemetry.domain.test_telemetry import make_telemetry

SITE_ID = SiteId("SITE-1")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_state(**overrides) -> EnergyState:
    telemetry = make_telemetry(site_id=SITE_ID, **overrides)
    return EnergyState.from_telemetry(telemetry, any_asset_offline=False)


def make_detector(**config_overrides) -> StatisticalDetector:
    return StatisticalDetector(AnomalyConfig(**config_overrides))


def test_no_flag_with_insufficient_history():
    detector = make_detector(min_history_for_baseline=5)
    history = [make_state(building_load=Power(20.0)) for _ in range(2)]
    state = make_state(building_load=Power(200.0))
    detections = detector.detect(state, history)
    assert not any(d.anomaly_type is AnomalyType.LOAD_SPIKE for d in detections)


def test_flags_load_spike_beyond_sigma_threshold():
    detector = make_detector(min_history_for_baseline=5, load_spike_sigma_threshold=3.0)
    history = [make_state(building_load=Power(20.0 + i % 2)) for i in range(10)]
    state = make_state(building_load=Power(500.0))
    detections = detector.detect(state, history)
    assert any(d.anomaly_type is AnomalyType.LOAD_SPIKE for d in detections)


def test_no_flag_for_load_within_normal_variation():
    detector = make_detector(min_history_for_baseline=5, load_spike_sigma_threshold=3.0)
    history = [make_state(building_load=Power(20.0 + i % 3)) for i in range(10)]
    state = make_state(building_load=Power(21.0))
    detections = detector.detect(state, history)
    assert not any(d.anomaly_type is AnomalyType.LOAD_SPIKE for d in detections)


def test_flags_sensor_failure_when_daylight_but_zero_output():
    detector = make_detector()
    state = make_state(irradiance_w_m2=800.0, solar_power=Power(0.0))
    detections = detector.detect(state, [])
    assert any(d.anomaly_type is AnomalyType.SENSOR_FAILURE for d in detections)


def test_no_flag_for_legitimate_night_zero_output():
    detector = make_detector()
    state = make_state(irradiance_w_m2=0.0, solar_power=Power(0.0))
    detections = detector.detect(state, [])
    assert not any(d.anomaly_type is AnomalyType.SENSOR_FAILURE for d in detections)


def test_no_flag_when_daylight_output_is_nonzero():
    detector = make_detector()
    state = make_state(irradiance_w_m2=800.0, solar_power=Power(50.0))
    detections = detector.detect(state, [])
    assert not any(d.anomaly_type is AnomalyType.SENSOR_FAILURE for d in detections)
