from datetime import UTC, datetime

import pytest

from solarops.decision.domain.confidence import ConfidenceBand
from solarops.execution.application.approval_engine import ApprovalEngine
from solarops.execution.domain.approval_request import ApprovalDecision
from solarops.execution.domain.command import Command
from solarops.execution.infrastructure.in_memory_approval_request_repository import (
    InMemoryApprovalRequestRepository,
)
from solarops.safety.domain.policy_result import PolicyResult
from solarops.safety.domain.risk_assessment import RiskAssessment
from solarops.safety.domain.safety_assessment import SafetyAssessment
from solarops.shared_kernel import (
    ActionType,
    ApprovalOutcome,
    AssetId,
    FixedClock,
    RecommendationId,
    RiskLevel,
    SiteId,
)

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_command_at_risk_assessed(level: RiskLevel) -> Command:
    command = Command.create(
        site_id=SiteId("SITE-1"),
        asset_id=AssetId("SITE-1-battery"),
        recommendation_id=RecommendationId.generate(),
        action=ActionType.CHARGE_BATTERY,
        params={},
        idempotency_key="idem-1",
        trace_id="trace-1",
        created_at=NOW,
    )
    command.apply_policy_result(PolicyResult(passed=True, evaluated_at=NOW))
    command.apply_safety_assessment(SafetyAssessment(passed=True, evaluated_at=NOW))
    command.apply_risk_assessment(RiskAssessment(level=level, assessed_at=NOW))
    return command


def make_engine() -> ApprovalEngine:
    return ApprovalEngine(InMemoryApprovalRequestRepository(), FixedClock(NOW))


def test_low_auto_approves_without_a_request():
    engine = make_engine()
    command = make_command_at_risk_assessed(RiskLevel.LOW)
    request = engine.route(command)
    assert request is None
    assert command.status.name == "AUTO_APPROVED"


def test_medium_auto_approves_without_a_request():
    engine = make_engine()
    command = make_command_at_risk_assessed(RiskLevel.MEDIUM)
    request = engine.route(command)
    assert request is None
    assert command.status.name == "AUTO_APPROVED"


def test_high_creates_a_pending_approval_request():
    engine = make_engine()
    command = make_command_at_risk_assessed(RiskLevel.HIGH)
    request = engine.route(command)
    assert request is not None
    assert request.is_pending
    assert command.status.name == "AWAITING_APPROVAL"


def test_decide_approved_moves_command_to_approved():
    engine = make_engine()
    command = make_command_at_risk_assessed(RiskLevel.HIGH)
    request = engine.route(command)
    decision = ApprovalDecision(outcome=ApprovalOutcome.APPROVED, decided_at=NOW)
    engine.decide(request, command, decision)
    assert command.status.name == "APPROVED"


def test_decide_rejected_moves_command_to_rejected_by_operator():
    engine = make_engine()
    command = make_command_at_risk_assessed(RiskLevel.HIGH)
    request = engine.route(command)
    decision = ApprovalDecision(outcome=ApprovalOutcome.REJECTED, decided_at=NOW)
    engine.decide(request, command, decision)
    assert command.status.name == "REJECTED_BY_OPERATOR"


def test_critical_raises_if_it_somehow_reaches_the_engine():
    engine = make_engine()
    command = make_command_at_risk_assessed(RiskLevel.CRITICAL)
    with pytest.raises(ValueError, match="CRITICAL"):
        engine.route(command)


# --- Phase 6d: confidence-driven escalation (Document 9 §8) ---


def test_low_risk_with_low_confidence_now_requires_approval():
    engine = make_engine()
    command = make_command_at_risk_assessed(RiskLevel.LOW)
    request = engine.route(command, confidence_band=ConfidenceBand.LOW)
    assert request is not None
    assert request.is_pending
    assert command.status.name == "AWAITING_APPROVAL"


def test_medium_risk_with_low_confidence_now_requires_approval():
    engine = make_engine()
    command = make_command_at_risk_assessed(RiskLevel.MEDIUM)
    request = engine.route(command, confidence_band=ConfidenceBand.LOW)
    assert request is not None
    assert command.status.name == "AWAITING_APPROVAL"


def test_low_risk_with_medium_or_high_confidence_still_auto_approves():
    for band in (ConfidenceBand.MEDIUM, ConfidenceBand.HIGH):
        engine = make_engine()
        command = make_command_at_risk_assessed(RiskLevel.LOW)
        request = engine.route(command, confidence_band=band)
        assert request is None
        assert command.status.name == "AUTO_APPROVED"


def test_high_risk_still_requires_approval_regardless_of_confidence_band():
    for band in (ConfidenceBand.HIGH, ConfidenceBand.MEDIUM, ConfidenceBand.LOW):
        engine = make_engine()
        command = make_command_at_risk_assessed(RiskLevel.HIGH)
        request = engine.route(command, confidence_band=band)
        assert request is not None
        assert command.status.name == "AWAITING_APPROVAL"


def test_critical_still_raises_even_with_low_confidence_band():
    engine = make_engine()
    command = make_command_at_risk_assessed(RiskLevel.CRITICAL)
    with pytest.raises(ValueError, match="CRITICAL"):
        engine.route(command, confidence_band=ConfidenceBand.LOW)
