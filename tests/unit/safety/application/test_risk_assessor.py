from datetime import UTC, datetime

from solarops.safety.application.risk_assessor import RiskAssessor
from solarops.safety.domain.command_intent import CommandIntent
from solarops.safety.domain.policy import Policy
from solarops.safety.domain.safety_assessment import SafetyAssessment
from solarops.safety.domain.safety_limits import SafetyLimits
from solarops.shared_kernel import (
    ActionType,
    AssetId,
    AssetOperatingMode,
    CommandId,
    FixedClock,
    InverterStatus,
    PolicyId,
    Power,
    RiskLevel,
    SiteId,
    StateOfCharge,
    Temperature,
)
from solarops.telemetry.domain.energy_state import EnergyState

from ...telemetry.domain.test_telemetry import make_telemetry

SITE_ID = SiteId("SITE-1")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)

PASSED = SafetyAssessment(passed=True, evaluated_at=NOW)


def make_assessor() -> RiskAssessor:
    return RiskAssessor(FixedClock(NOW))


def make_policy(**overrides) -> Policy:
    defaults = dict(
        policy_id=PolicyId.generate(),
        site_id=SITE_ID,
        version=1,
        max_battery_soc=StateOfCharge(95.0),
        min_battery_soc=StateOfCharge(10.0),
    )
    defaults.update(overrides)
    return Policy(**defaults)


def make_limits(**overrides) -> SafetyLimits:
    defaults = dict(
        battery_min_soc=StateOfCharge(10.0),
        battery_max_soc=StateOfCharge(95.0),
        battery_max_temp=Temperature(45.0),
        battery_max_charge_power=Power(50.0),
        battery_max_discharge_power=Power(50.0),
        inverter_max_power=Power(120.0),
    )
    defaults.update(overrides)
    return SafetyLimits(**defaults)


def make_intent(**overrides) -> CommandIntent:
    defaults = dict(
        command_id=CommandId.generate(),
        site_id=SITE_ID,
        asset_id=AssetId("ASSET-battery-1"),
        action=ActionType.CHARGE_BATTERY,
        params={},
    )
    defaults.update(overrides)
    return CommandIntent(**defaults)


def make_state(**overrides) -> EnergyState:
    telemetry = make_telemetry(site_id=SITE_ID, **overrides)
    return EnergyState.from_telemetry(telemetry, any_asset_offline=False)


def test_critical_when_safety_assessment_failed():
    assessor = make_assessor()
    failed = SafetyAssessment(passed=False, failed_checks=("x",), evaluated_at=NOW)
    result = assessor.assess(make_intent(), make_state(), make_policy(), make_limits(), failed)
    assert result.level is RiskLevel.CRITICAL


def test_critical_when_inverter_in_fault_mode():
    assessor = make_assessor()
    state = make_state(inverter_status=InverterStatus.FAULT_COMM_LOSS)
    result = assessor.assess(make_intent(), state, make_policy(), make_limits(), PASSED)
    assert result.level is RiskLevel.CRITICAL


def test_critical_when_asset_in_emergency_mode():
    assessor = make_assessor()
    intent = make_intent(asset_operating_mode=AssetOperatingMode.EMERGENCY)
    result = assessor.assess(intent, make_state(), make_policy(), make_limits(), PASSED)
    assert result.level is RiskLevel.CRITICAL


def test_critical_when_building_load_shed_asset_in_emergency_mode():
    # Building-specific: EMERGENCY is CRITICAL regardless of which asset/action.
    assessor = make_assessor()
    intent = make_intent(
        action=ActionType.SHED_LOAD,
        params={"fraction": 0.1},
        asset_operating_mode=AssetOperatingMode.EMERGENCY,
    )
    result = assessor.assess(intent, make_state(), make_policy(), make_limits(), PASSED)
    assert result.level is RiskLevel.CRITICAL


def test_critical_when_near_hard_limit_despite_passing():
    assessor = make_assessor()
    # battery_soc within 5% of the 95% max -> near-edge, despite passing.
    state = make_state(battery_soc=StateOfCharge(94.0))
    result = assessor.assess(
        make_intent(action=ActionType.CHARGE_BATTERY), state, make_policy(), make_limits(), PASSED
    )
    assert result.level is RiskLevel.CRITICAL


def test_high_on_large_power_swing():
    assessor = make_assessor()
    state = make_state(battery_soc=StateOfCharge(50.0))
    intent = make_intent(action=ActionType.CHARGE_BATTERY, params={"power_kw": 45.0})
    limits = make_limits(battery_max_charge_power=Power(50.0))
    result = assessor.assess(intent, state, make_policy(), limits, PASSED)
    assert result.level is RiskLevel.HIGH


def test_high_during_maintenance_mode():
    assessor = make_assessor()
    state = make_state(battery_soc=StateOfCharge(50.0))
    result = assessor.assess(
        make_intent(), state, make_policy(maintenance_mode=True), make_limits(), PASSED
    )
    assert result.level is RiskLevel.HIGH


def test_medium_on_moderate_margin():
    assessor = make_assessor()
    # 85% SOC vs [10,95] range -> (95-85)/85range = 10/85 ≈ 11.8%, between 5% and 25%.
    state = make_state(battery_soc=StateOfCharge(85.0))
    result = assessor.assess(
        make_intent(action=ActionType.CHARGE_BATTERY), state, make_policy(), make_limits(), PASSED
    )
    assert result.level is RiskLevel.MEDIUM


def test_low_on_comfortable_margin_normal_operation():
    assessor = make_assessor()
    state = make_state(battery_soc=StateOfCharge(50.0))
    result = assessor.assess(
        make_intent(action=ActionType.CHARGE_BATTERY), state, make_policy(), make_limits(), PASSED
    )
    assert result.level is RiskLevel.LOW
