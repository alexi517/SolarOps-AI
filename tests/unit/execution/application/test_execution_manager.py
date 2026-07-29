from datetime import UTC, datetime

from solarops.execution.application.execution_manager import ExecutionManager
from solarops.execution.domain.approval_request import ApprovalDecision
from solarops.execution.domain.command import Command
from solarops.safety.domain.policy_result import PolicyResult
from solarops.safety.domain.risk_assessment import RiskAssessment
from solarops.safety.domain.safety_assessment import SafetyAssessment
from solarops.shared_kernel import (
    ActionType,
    ApprovalOutcome,
    AssetId,
    ExecutionOutcome,
    FixedClock,
    RecommendationId,
    RiskLevel,
    SiteId,
)

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


class FakeHardwareInterface:
    def __init__(self, outcomes):
        self._outcomes = list(outcomes)
        self.calls = []

    def send(self, *, asset_id, action, params):
        self.calls.append((asset_id, action, dict(params)))
        return self._outcomes.pop(0)


class RaisingHardwareInterface:
    def send(self, *, asset_id, action, params):
        raise ConnectionError("hardware unreachable")


def make_dispatchable_command() -> Command:
    command = Command.create(
        site_id=SiteId("SITE-1"),
        asset_id=AssetId("SITE-1-battery"),
        recommendation_id=RecommendationId.generate(),
        action=ActionType.CHARGE_BATTERY,
        params={"power_kw": 20.0},
        idempotency_key="idem-1",
        trace_id="trace-1",
        created_at=NOW,
    )
    command.apply_policy_result(PolicyResult(passed=True, evaluated_at=NOW))
    command.apply_safety_assessment(SafetyAssessment(passed=True, evaluated_at=NOW))
    command.apply_risk_assessment(RiskAssessment(level=RiskLevel.LOW, assessed_at=NOW))
    command.auto_approve()
    return command


def test_success_moves_command_to_executed():
    hardware = FakeHardwareInterface([ExecutionOutcome.SUCCESS])
    manager = ExecutionManager(hardware, FixedClock(NOW))
    command = make_dispatchable_command()

    result = manager.dispatch(command)

    assert result.outcome is ExecutionOutcome.SUCCESS
    assert command.status.name == "EXECUTED"
    assert hardware.calls[0][1] is ActionType.CHARGE_BATTERY


def test_failed_outcome_moves_command_to_execution_failed():
    hardware = FakeHardwareInterface([ExecutionOutcome.FAILED])
    manager = ExecutionManager(hardware, FixedClock(NOW))
    command = make_dispatchable_command()

    manager.dispatch(command)

    assert command.status.name == "EXECUTION_FAILED"


def test_timeout_retries_up_to_max_then_times_out():
    hardware = FakeHardwareInterface(
        [ExecutionOutcome.TIMED_OUT, ExecutionOutcome.TIMED_OUT, ExecutionOutcome.TIMED_OUT]
    )
    manager = ExecutionManager(hardware, FixedClock(NOW), max_retries=2)
    command = make_dispatchable_command()

    result = manager.dispatch(command)

    assert result.retry_count == 2
    assert len(hardware.calls) == 3  # 1 initial + 2 retries
    assert command.status.name == "TIMED_OUT"


def test_timeout_that_recovers_on_retry_succeeds():
    hardware = FakeHardwareInterface([ExecutionOutcome.TIMED_OUT, ExecutionOutcome.SUCCESS])
    manager = ExecutionManager(hardware, FixedClock(NOW), max_retries=2)
    command = make_dispatchable_command()

    result = manager.dispatch(command)

    assert result.outcome is ExecutionOutcome.SUCCESS
    assert command.status.name == "EXECUTED"


def test_blocked_outcome_is_a_dispatch_failure_not_execution_failure():
    hardware = FakeHardwareInterface([ExecutionOutcome.BLOCKED])
    manager = ExecutionManager(hardware, FixedClock(NOW))
    command = make_dispatchable_command()

    manager.dispatch(command)

    assert command.status.name == "DISPATCH_FAILED"


def test_hardware_exception_never_assumes_success():
    manager = ExecutionManager(RaisingHardwareInterface(), FixedClock(NOW))
    command = make_dispatchable_command()

    result = manager.dispatch(command)

    assert result.outcome is ExecutionOutcome.FAILED
    assert command.status.name == "DISPATCH_FAILED"


def test_modified_approval_params_override_command_params():
    command = Command.create(
        site_id=SiteId("SITE-1"),
        asset_id=AssetId("SITE-1-battery"),
        recommendation_id=RecommendationId.generate(),
        action=ActionType.CHARGE_BATTERY,
        params={"power_kw": 20.0},
        idempotency_key="idem-2",
        trace_id="trace-2",
        created_at=NOW,
    )
    command.apply_policy_result(PolicyResult(passed=True, evaluated_at=NOW))
    command.apply_safety_assessment(SafetyAssessment(passed=True, evaluated_at=NOW))
    command.apply_risk_assessment(RiskAssessment(level=RiskLevel.HIGH, assessed_at=NOW))
    command.await_approval()
    command.approve(
        ApprovalDecision(
            outcome=ApprovalOutcome.MODIFIED, decided_at=NOW, modified_params={"power_kw": 5.0}
        )
    )

    hardware = FakeHardwareInterface([ExecutionOutcome.SUCCESS])
    manager = ExecutionManager(hardware, FixedClock(NOW))
    manager.dispatch(command)

    assert hardware.calls[0][2] == {"power_kw": 5.0}
