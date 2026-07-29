from datetime import UTC, datetime

import pytest

from solarops.safety.application.safety_validator import SafetyValidator
from solarops.safety.domain.command_intent import CommandIntent
from solarops.safety.domain.safety_limits import SafetyLimits
from solarops.safety.infrastructure.static_safety_limits_provider import StaticSafetyLimitsProvider
from solarops.shared_kernel import (
    ActionType,
    AssetId,
    AssetOperatingMode,
    CommandId,
    FailSafeTriggered,
    FixedClock,
    Frequency,
    GridStatus,
    InverterStatus,
    Power,
    SiteId,
    StateOfCharge,
    Temperature,
    Voltage,
)
from solarops.telemetry.domain.energy_state import EnergyState
from solarops.telemetry.infrastructure.in_memory_state_store import InMemoryStateStore

from ...telemetry.domain.test_telemetry import make_telemetry

SITE_ID = SiteId("SITE-1")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


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


def make_validator(limits: SafetyLimits | None, state: EnergyState | None) -> SafetyValidator:
    store = InMemoryStateStore()
    if state is not None:
        store.set(state)
    provider = StaticSafetyLimitsProvider(limits) if limits is not None else _NoLimitsProvider()
    return SafetyValidator(provider, store, FixedClock(NOW))


class _NoLimitsProvider:
    def get_limits(self, site_id):
        return None


def make_state(**telemetry_overrides) -> EnergyState:
    telemetry = make_telemetry(site_id=SITE_ID, **telemetry_overrides)
    return EnergyState.from_telemetry(telemetry, any_asset_offline=False)


def test_routine_charge_passes():
    validator = make_validator(make_limits(), make_state(battery_soc=StateOfCharge(50.0)))
    assessment = validator.validate(make_intent(params={"power_kw": 20.0}))
    assert assessment.passed is True
    assert assessment.failed_checks == ()


def test_charge_blocked_when_soc_already_at_max():
    validator = make_validator(make_limits(), make_state(battery_soc=StateOfCharge(95.0)))
    assessment = validator.validate(make_intent(action=ActionType.CHARGE_BATTERY))
    assert assessment.passed is False
    assert any("already at/above max" in c for c in assessment.failed_checks)


def test_discharge_blocked_when_soc_already_at_min():
    validator = make_validator(make_limits(), make_state(battery_soc=StateOfCharge(10.0)))
    assessment = validator.validate(make_intent(action=ActionType.DISCHARGE_BATTERY))
    assert assessment.passed is False
    assert any("already at/below min" in c for c in assessment.failed_checks)


def test_charge_blocked_by_overtemp():
    validator = make_validator(make_limits(), make_state(battery_temp=Temperature(50.0)))
    assessment = validator.validate(make_intent(action=ActionType.CHARGE_BATTERY))
    assert assessment.passed is False
    assert any("temperature" in c for c in assessment.failed_checks)


def test_charge_power_exceeding_limit_is_blocked():
    validator = make_validator(make_limits(battery_max_charge_power=Power(30.0)), make_state())
    assessment = validator.validate(
        make_intent(action=ActionType.CHARGE_BATTERY, params={"power_kw": 40.0})
    )
    assert assessment.passed is False
    assert any("exceeds max" in c for c in assessment.failed_checks)


def test_inverter_status_not_allowed_is_blocked():
    validator = make_validator(
        make_limits(), make_state(inverter_status=InverterStatus.FAULT_OVERTEMP)
    )
    assessment = validator.validate(make_intent(action=ActionType.CHARGE_BATTERY))
    assert assessment.passed is False
    assert any("inverter status" in c for c in assessment.failed_checks)


def test_inverter_power_exceeding_limit_is_blocked():
    validator = make_validator(
        make_limits(inverter_max_power=Power(10.0)), make_state(inverter_output=Power(50.0))
    )
    assessment = validator.validate(make_intent(action=ActionType.CHARGE_BATTERY))
    assert assessment.passed is False
    assert any("inverter output" in c for c in assessment.failed_checks)


def test_grid_not_connected_blocks_import():
    validator = make_validator(make_limits(), make_state(grid_status=GridStatus.OUTAGE))
    assessment = validator.validate(make_intent(action=ActionType.IMPORT_FROM_GRID))
    assert assessment.passed is False
    assert any("grid status" in c for c in assessment.failed_checks)


def test_grid_voltage_outside_tolerance_blocks_export():
    validator = make_validator(
        make_limits(), make_state(grid_status=GridStatus.CONNECTED, grid_voltage=Voltage(500.0))
    )
    assessment = validator.validate(make_intent(action=ActionType.EXPORT_TO_GRID))
    assert assessment.passed is False
    assert any("voltage" in c for c in assessment.failed_checks)


def test_grid_frequency_outside_tolerance_blocks_export():
    validator = make_validator(
        make_limits(), make_state(grid_status=GridStatus.CONNECTED, grid_frequency=Frequency(52.0))
    )
    assessment = validator.validate(make_intent(action=ActionType.EXPORT_TO_GRID))
    assert assessment.passed is False
    assert any("frequency" in c for c in assessment.failed_checks)


def test_emergency_operating_mode_blocks_unconditionally():
    validator = make_validator(make_limits(), make_state())
    intent = make_intent(
        action=ActionType.CHARGE_BATTERY, asset_operating_mode=AssetOperatingMode.EMERGENCY
    )
    assessment = validator.validate(intent)
    assert assessment.passed is False
    assert any("EMERGENCY" in c for c in assessment.failed_checks)


def test_emergency_operating_mode_blocks_building_load_shed_too():
    # The "Building" catalog item is two checks together (critical-load
    # protection + emergency mode) — this proves EMERGENCY blocks a building
    # action specifically, not just battery actions.
    validator = make_validator(make_limits(building_max_shed_fraction=1.0), make_state())
    intent = make_intent(
        action=ActionType.SHED_LOAD,
        params={"fraction": 0.1},
        asset_operating_mode=AssetOperatingMode.EMERGENCY,
    )
    assessment = validator.validate(intent)
    assert assessment.passed is False
    assert any("EMERGENCY" in c for c in assessment.failed_checks)


def test_shed_fraction_exceeding_hard_ceiling_is_blocked():
    validator = make_validator(make_limits(building_max_shed_fraction=0.1), make_state())
    intent = make_intent(action=ActionType.SHED_LOAD, params={"fraction": 0.3})
    assessment = validator.validate(intent)
    assert assessment.passed is False
    assert any("shed fraction" in c for c in assessment.failed_checks)


def test_shed_fraction_within_hard_ceiling_passes():
    validator = make_validator(make_limits(building_max_shed_fraction=0.5), make_state())
    intent = make_intent(action=ActionType.SHED_LOAD, params={"fraction": 0.2})
    assessment = validator.validate(intent)
    assert assessment.passed is True


def test_fail_safe_when_state_unavailable():
    validator = make_validator(make_limits(), None)
    with pytest.raises(FailSafeTriggered):
        validator.validate(make_intent())


def test_fail_safe_when_limits_unavailable():
    validator = make_validator(None, make_state())
    with pytest.raises(FailSafeTriggered):
        validator.validate(make_intent())
