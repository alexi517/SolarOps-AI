from datetime import UTC, datetime

from solarops.anomaly.application.rule_detector import RuleDetector
from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.infrastructure.config import AnomalyConfig
from solarops.shared_kernel import GridStatus, InverterStatus, SiteId, Temperature
from solarops.telemetry.domain.energy_state import EnergyState

from ...telemetry.domain.test_telemetry import make_telemetry

SITE_ID = SiteId("SITE-1")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_state(**overrides) -> EnergyState:
    telemetry = make_telemetry(site_id=SITE_ID, **overrides)
    return EnergyState.from_telemetry(telemetry, any_asset_offline=False)


def make_detector(**config_overrides) -> RuleDetector:
    return RuleDetector(AnomalyConfig(**config_overrides))


def test_flags_battery_overheating():
    detector = make_detector(battery_overheat_temp_c=45.0)
    state = make_state(battery_temp=Temperature(50.0))
    detections = detector.detect(state, [])
    assert any(d.anomaly_type is AnomalyType.BATTERY_OVERHEATING for d in detections)


def test_no_flag_when_battery_temp_within_limit():
    detector = make_detector(battery_overheat_temp_c=45.0)
    state = make_state(battery_temp=Temperature(30.0))
    detections = detector.detect(state, [])
    assert not any(d.anomaly_type is AnomalyType.BATTERY_OVERHEATING for d in detections)


def test_flags_grid_instability_on_outage():
    detector = make_detector()
    state = make_state(grid_status=GridStatus.OUTAGE)
    detections = detector.detect(state, [])
    assert any(d.anomaly_type is AnomalyType.GRID_INSTABILITY for d in detections)


def test_flags_grid_instability_on_unstable():
    detector = make_detector()
    state = make_state(grid_status=GridStatus.UNSTABLE)
    detections = detector.detect(state, [])
    assert any(d.anomaly_type is AnomalyType.GRID_INSTABILITY for d in detections)


def test_flags_communication_loss_not_generic_inverter_fault():
    detector = make_detector()
    state = make_state(inverter_status=InverterStatus.FAULT_COMM_LOSS)
    detections = detector.detect(state, [])
    types = {d.anomaly_type for d in detections}
    assert AnomalyType.COMMUNICATION_LOSS in types
    assert AnomalyType.INVERTER_FAULT not in types


def test_flags_inverter_fault_for_overtemp():
    detector = make_detector()
    state = make_state(inverter_status=InverterStatus.FAULT_OVERTEMP)
    detections = detector.detect(state, [])
    assert any(d.anomaly_type is AnomalyType.INVERTER_FAULT for d in detections)


def test_no_flags_during_normal_operation():
    detector = make_detector()
    state = make_state()
    detections = detector.detect(state, [])
    assert detections == []


def test_detected_at_matches_state_timestamp_not_wall_clock():
    detector = make_detector()
    state = make_state(battery_temp=Temperature(50.0))
    detections = detector.detect(state, [])
    assert detections[0].detected_at == state.timestamp
