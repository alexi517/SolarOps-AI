from datetime import UTC, datetime

from solarops.execution.application.verification_service import VerificationService
from solarops.execution.domain.command import Command
from solarops.shared_kernel import (
    ActionType,
    AssetId,
    BatteryMode,
    FixedClock,
    RecommendationId,
    SiteId,
)
from solarops.telemetry.domain.energy_state import EnergyState

from ...telemetry.domain.test_telemetry import make_telemetry

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)
SITE_ID = SiteId("SITE-1")


class FakeTelemetryReader:
    def __init__(self, state: EnergyState | None) -> None:
        self._state = state

    def get_current(self, site_id):
        return self._state


def make_command(action: ActionType) -> Command:
    return Command.create(
        site_id=SITE_ID,
        asset_id=AssetId("SITE-1-battery"),
        recommendation_id=RecommendationId.generate(),
        action=action,
        params={},
        idempotency_key="idem-1",
        trace_id="trace-1",
        created_at=NOW,
    )


def make_state(**overrides) -> EnergyState:
    telemetry = make_telemetry(site_id=SITE_ID, **overrides)
    return EnergyState.from_telemetry(telemetry, any_asset_offline=False)


def test_charge_battery_verified_when_battery_mode_is_charging():
    reader = FakeTelemetryReader(make_state(battery_mode=BatteryMode.CHARGING))
    service = VerificationService(reader, FixedClock(NOW))
    result = service.verify(make_command(ActionType.CHARGE_BATTERY))
    assert result.passed is True


def test_charge_battery_fails_verification_when_battery_mode_did_not_change():
    reader = FakeTelemetryReader(make_state(battery_mode=BatteryMode.IDLE))
    service = VerificationService(reader, FixedClock(NOW))
    result = service.verify(make_command(ActionType.CHARGE_BATTERY))
    assert result.passed is False
    assert "IDLE" in result.observed


def test_discharge_battery_verified_when_battery_mode_is_discharging():
    reader = FakeTelemetryReader(make_state(battery_mode=BatteryMode.DISCHARGING))
    service = VerificationService(reader, FixedClock(NOW))
    result = service.verify(make_command(ActionType.DISCHARGE_BATTERY))
    assert result.passed is True


def test_action_without_a_specific_rule_uses_generic_fault_code_check():
    reader = FakeTelemetryReader(make_state(fault_codes=[]))
    service = VerificationService(reader, FixedClock(NOW))
    result = service.verify(make_command(ActionType.SHED_LOAD))
    assert result.passed is True


def test_generic_check_fails_when_fault_codes_present():
    reader = FakeTelemetryReader(make_state(fault_codes=["GRID_OUTAGE"]))
    service = VerificationService(reader, FixedClock(NOW))
    result = service.verify(make_command(ActionType.SHED_LOAD))
    assert result.passed is False


def test_no_telemetry_fails_verification():
    reader = FakeTelemetryReader(None)
    service = VerificationService(reader, FixedClock(NOW))
    result = service.verify(make_command(ActionType.CHARGE_BATTERY))
    assert result.passed is False
    assert "no telemetry" in result.observed
