from datetime import UTC, datetime

from solarops.safety.application.policy_validator import PolicyValidator
from solarops.safety.domain.command_intent import CommandIntent
from solarops.safety.domain.events import PolicyViolated
from solarops.safety.domain.policy import Policy
from solarops.safety.infrastructure.in_memory_policy_repository import InMemoryPolicyRepository
from solarops.shared_kernel import (
    ActionType,
    AssetId,
    CommandId,
    FixedClock,
    PolicyId,
    SiteId,
    StateOfCharge,
)

SITE_ID = SiteId("SITE-1")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


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


def make_validator(policy: Policy | None) -> PolicyValidator:
    repo = InMemoryPolicyRepository()
    if policy is not None:
        repo.save(policy)
    return PolicyValidator(repo, FixedClock(NOW))


def test_routine_command_passes():
    validator = make_validator(make_policy())
    result, events = validator.validate(make_intent(params={"target_soc": 80.0}))
    assert result.passed is True
    assert result.violations == ()
    assert events == []


def test_missing_policy_fails_closed():
    validator = make_validator(None)
    result, events = validator.validate(make_intent())
    assert result.passed is False
    assert "no policy configured" in result.violations[0]
    assert isinstance(events[0], PolicyViolated)


def test_maintenance_mode_blocks_charging():
    validator = make_validator(make_policy(maintenance_mode=True))
    result, events = validator.validate(make_intent(action=ActionType.CHARGE_BATTERY))
    assert result.passed is False
    assert "maintenance mode" in result.violations[0]
    assert isinstance(events[0], PolicyViolated)


def test_maintenance_override_allows_charging():
    validator = make_validator(make_policy(maintenance_mode=True, maintenance_override=True))
    result, _events = validator.validate(make_intent(action=ActionType.CHARGE_BATTERY))
    assert result.passed is True


def test_shed_fraction_exceeding_ceiling_is_blocked():
    validator = make_validator(make_policy(max_shed_fraction=0.2))
    result, events = validator.validate(
        make_intent(action=ActionType.SHED_LOAD, params={"fraction": 0.5})
    )
    assert result.passed is False
    assert "exceeds" in result.violations[0]
    assert isinstance(events[0], PolicyViolated)


def test_shed_fraction_within_ceiling_passes():
    validator = make_validator(make_policy(max_shed_fraction=0.5))
    result, _events = validator.validate(
        make_intent(action=ActionType.SHED_LOAD, params={"fraction": 0.2})
    )
    assert result.passed is True


def test_charge_target_soc_above_policy_max_is_blocked():
    validator = make_validator(make_policy(max_battery_soc=StateOfCharge(90.0)))
    result, events = validator.validate(
        make_intent(action=ActionType.CHARGE_BATTERY, params={"target_soc": 95.0})
    )
    assert result.passed is False
    assert "exceeds policy max" in result.violations[0]
    assert isinstance(events[0], PolicyViolated)


def test_discharge_target_soc_below_policy_min_is_blocked():
    validator = make_validator(make_policy(min_battery_soc=StateOfCharge(20.0)))
    result, events = validator.validate(
        make_intent(action=ActionType.DISCHARGE_BATTERY, params={"target_soc": 15.0})
    )
    assert result.passed is False
    assert "below policy min" in result.violations[0]
    assert isinstance(events[0], PolicyViolated)
