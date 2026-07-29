from datetime import UTC, datetime, timedelta

import pytest

from solarops.execution.domain.approval_request import ApprovalDecision, ApprovalRequest
from solarops.shared_kernel import (
    ApprovalOutcome,
    ApprovalRequestId,
    CommandId,
    InvalidStateTransition,
    OperatorId,
    RiskLevel,
    SiteId,
)

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_request() -> ApprovalRequest:
    return ApprovalRequest(
        approval_request_id=ApprovalRequestId.generate(),
        command_id=CommandId.generate(),
        site_id=SiteId("SITE-1"),
        risk_level=RiskLevel.HIGH,
        requested_at=NOW,
        timeout_at=NOW + timedelta(minutes=30),
    )


def test_is_pending_until_decided():
    request = make_request()
    assert request.is_pending is True
    decision = ApprovalDecision(
        outcome=ApprovalOutcome.APPROVED, decided_at=NOW, operator_id=OperatorId("OP-1")
    )
    request.decide(decision)
    assert request.is_pending is False
    assert request.decision.outcome is ApprovalOutcome.APPROVED


def test_cannot_decide_twice():
    request = make_request()
    request.decide(ApprovalDecision(outcome=ApprovalOutcome.APPROVED, decided_at=NOW))
    with pytest.raises(InvalidStateTransition):
        request.decide(ApprovalDecision(outcome=ApprovalOutcome.REJECTED, decided_at=NOW))


def test_expire_sets_expired_outcome_with_no_operator():
    request = make_request()
    request.expire(NOW + timedelta(minutes=31))
    assert request.decision.outcome is ApprovalOutcome.EXPIRED
    assert request.decision.operator_id is None


def test_cannot_expire_an_already_decided_request():
    request = make_request()
    request.decide(ApprovalDecision(outcome=ApprovalOutcome.APPROVED, decided_at=NOW))
    with pytest.raises(InvalidStateTransition):
        request.expire(NOW + timedelta(minutes=31))


def test_modified_decision_carries_modified_params():
    request = make_request()
    request.decide(
        ApprovalDecision(
            outcome=ApprovalOutcome.MODIFIED,
            decided_at=NOW,
            operator_id=OperatorId("OP-1"),
            modified_params={"power_kw": 10.0},
        )
    )
    assert request.decision.modified_params == {"power_kw": 10.0}
