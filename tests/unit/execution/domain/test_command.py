from datetime import UTC, datetime

import pytest

from solarops.execution.domain.approval_request import ApprovalDecision
from solarops.execution.domain.command import Command
from solarops.execution.domain.execution_result import ExecutionResult
from solarops.execution.domain.verification_result import VerificationResult
from solarops.safety.domain.policy_result import PolicyResult
from solarops.safety.domain.risk_assessment import RiskAssessment
from solarops.safety.domain.safety_assessment import SafetyAssessment
from solarops.shared_kernel import (
    ActionType,
    ApprovalOutcome,
    AssetId,
    CommandStatus,
    ExecutionOutcome,
    InvalidStateTransition,
    RecommendationId,
    RiskLevel,
    SiteId,
)

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_command(**overrides) -> Command:
    defaults = dict(
        site_id=SiteId("SITE-1"),
        asset_id=AssetId("SITE-1-battery"),
        recommendation_id=RecommendationId.generate(),
        action=ActionType.CHARGE_BATTERY,
        params={"power_kw": 20.0},
        idempotency_key="idem-1",
        trace_id="trace-1",
        created_at=NOW,
    )
    defaults.update(overrides)
    return Command.create(**defaults)


def passing_policy_result() -> PolicyResult:
    return PolicyResult(passed=True, evaluated_at=NOW)


def failing_policy_result() -> PolicyResult:
    return PolicyResult(passed=False, violations=("x",), evaluated_at=NOW)


def passing_safety_assessment() -> SafetyAssessment:
    return SafetyAssessment(passed=True, evaluated_at=NOW)


def failing_safety_assessment() -> SafetyAssessment:
    return SafetyAssessment(passed=False, failed_checks=("x",), evaluated_at=NOW)


def risk_assessment(level: RiskLevel) -> RiskAssessment:
    return RiskAssessment(level=level, assessed_at=NOW)


def to_risk_assessed(command: Command, level: RiskLevel = RiskLevel.LOW) -> Command:
    command.apply_policy_result(passing_policy_result())
    command.apply_safety_assessment(passing_safety_assessment())
    command.apply_risk_assessment(risk_assessment(level))
    return command


def to_dispatchable(command: Command, level: RiskLevel = RiskLevel.LOW) -> Command:
    to_risk_assessed(command, level)
    command.auto_approve()
    return command


def to_executed(command: Command) -> Command:
    to_dispatchable(command)
    command.dispatch()
    command.acknowledge()
    command.mark_executed(ExecutionResult(outcome=ExecutionOutcome.SUCCESS, dispatched_at=NOW))
    return command


# --- creation ---


def test_create_starts_planned():
    command = make_command()
    assert command.status is CommandStatus.PLANNED


# --- policy gate ---


def test_policy_pass_moves_to_policy_validated():
    command = make_command()
    command.apply_policy_result(passing_policy_result())
    assert command.status is CommandStatus.POLICY_VALIDATED


def test_policy_fail_moves_to_rejected_by_policy_terminal():
    command = make_command()
    command.apply_policy_result(failing_policy_result())
    assert command.status is CommandStatus.REJECTED_BY_POLICY
    assert command.status.is_terminal


def test_policy_result_cannot_be_applied_twice():
    command = make_command()
    command.apply_policy_result(passing_policy_result())
    with pytest.raises(InvalidStateTransition):
        command.apply_policy_result(passing_policy_result())


# --- safety gate ---


def test_safety_pass_moves_to_safety_validated():
    command = make_command()
    command.apply_policy_result(passing_policy_result())
    command.apply_safety_assessment(passing_safety_assessment())
    assert command.status is CommandStatus.SAFETY_VALIDATED


def test_safety_fail_moves_to_blocked_by_safety_terminal():
    command = make_command()
    command.apply_policy_result(passing_policy_result())
    command.apply_safety_assessment(failing_safety_assessment())
    assert command.status is CommandStatus.BLOCKED_BY_SAFETY
    assert command.status.is_terminal


def test_safety_cannot_be_applied_before_policy():
    command = make_command()
    with pytest.raises(InvalidStateTransition):
        command.apply_safety_assessment(passing_safety_assessment())


# --- risk gate + routing ---


def test_risk_assessment_moves_to_risk_assessed():
    command = make_command()
    command.apply_policy_result(passing_policy_result())
    command.apply_safety_assessment(passing_safety_assessment())
    command.apply_risk_assessment(risk_assessment(RiskLevel.LOW))
    assert command.status is CommandStatus.RISK_ASSESSED


def test_low_or_medium_auto_approves():
    command = to_risk_assessed(make_command(), RiskLevel.MEDIUM)
    command.auto_approve()
    assert command.status is CommandStatus.AUTO_APPROVED


def test_high_awaits_approval():
    command = to_risk_assessed(make_command(), RiskLevel.HIGH)
    command.await_approval()
    assert command.status is CommandStatus.AWAITING_APPROVAL


def test_critical_rejects_and_is_never_dispatchable():
    command = to_risk_assessed(make_command(), RiskLevel.CRITICAL)
    command.reject_by_risk()
    assert command.status is CommandStatus.REJECTED_BY_RISK
    assert command.status.is_terminal
    with pytest.raises(InvalidStateTransition):
        command.dispatch()


# --- approval ---


def test_approve_from_awaiting_approval():
    command = to_risk_assessed(make_command(), RiskLevel.HIGH)
    command.await_approval()
    decision = ApprovalDecision(outcome=ApprovalOutcome.APPROVED, decided_at=NOW)
    command.approve(decision)
    assert command.status is CommandStatus.APPROVED


def test_reject_by_operator_is_terminal():
    command = to_risk_assessed(make_command(), RiskLevel.HIGH)
    command.await_approval()
    decision = ApprovalDecision(outcome=ApprovalOutcome.REJECTED, decided_at=NOW)
    command.reject_by_operator(decision)
    assert command.status is CommandStatus.REJECTED_BY_OPERATOR
    assert command.status.is_terminal


def test_expire_approval_is_terminal():
    command = to_risk_assessed(make_command(), RiskLevel.HIGH)
    command.await_approval()
    decision = ApprovalDecision(outcome=ApprovalOutcome.EXPIRED, decided_at=NOW)
    command.expire_approval(decision)
    assert command.status is CommandStatus.TIMED_OUT
    assert command.status.is_terminal


# --- dispatch / execution ---


def test_dispatch_requires_auto_approved_or_approved():
    # RISK_ASSESSED -> AWAITING_APPROVAL is not dispatchable.
    command = to_risk_assessed(make_command(), RiskLevel.HIGH)
    command.await_approval()
    with pytest.raises(InvalidStateTransition):
        command.dispatch()


def test_dispatch_then_acknowledge_then_execute():
    command = to_dispatchable(make_command())
    command.dispatch()
    assert command.status is CommandStatus.DISPATCHED
    command.acknowledge()
    assert command.status is CommandStatus.ACKNOWLEDGED
    result = ExecutionResult(outcome=ExecutionOutcome.SUCCESS, dispatched_at=NOW)
    command.mark_executed(result)
    assert command.status is CommandStatus.EXECUTED


def test_dispatch_failure_is_terminal():
    command = to_dispatchable(make_command())
    command.dispatch()
    command.mark_dispatch_failed()
    assert command.status is CommandStatus.DISPATCH_FAILED
    assert command.status.is_terminal


# --- verification (ADR-011: acknowledgement alone never completes a command) ---


def test_complete_requires_verified_status():
    command = to_dispatchable(make_command())
    command.dispatch()
    command.acknowledge()
    command.mark_executed(ExecutionResult(outcome=ExecutionOutcome.SUCCESS, dispatched_at=NOW))
    with pytest.raises(InvalidStateTransition):
        command.complete()  # EXECUTED is not VERIFIED — must verify() first


def test_verify_pass_then_complete():
    command = to_executed(make_command())
    command.verify(VerificationResult(passed=True, expected="x", observed="x", verified_at=NOW))
    assert command.status is CommandStatus.VERIFIED
    command.complete()
    assert command.status is CommandStatus.COMPLETED
    assert command.status.is_success


def test_verify_fail_blocks_completion_permanently():
    command = to_executed(make_command())
    command.verify(VerificationResult(passed=False, expected="x", observed="y", verified_at=NOW))
    assert command.status is CommandStatus.VERIFICATION_FAILED
    assert command.status.is_terminal
    with pytest.raises(InvalidStateTransition):
        command.complete()


# --- cancellation ---


def test_cancel_from_non_terminal_state():
    command = make_command()
    command.cancel()
    assert command.status is CommandStatus.CANCELLED


def test_cancel_from_terminal_state_raises():
    command = make_command()
    command.apply_policy_result(failing_policy_result())
    with pytest.raises(InvalidStateTransition):
        command.cancel()
