"""ApprovalEngine — routes a risk-assessed Command through CESF §8's approval path.

CRITICAL never reaches this class — the pipeline rejects at the risk gate
directly (``RiskLevel.CRITICAL.is_auto_rejected``), before ``ApprovalEngine``
is even called. This only ever sees LOW, MEDIUM, or HIGH.

Phase 6d (Document 9 §8) adds the confidence-driven escalation rule here —
this is "the point where the approval path is decided" the brief calls out.
Confidence can only ever *add* a reason to require approval, never remove
one: ``requires_approval`` below is ``requires_manual_approval OR
confidence_is_low``, so a HIGH risk level (which already sets
``requires_manual_approval``) is completely unaffected by confidence, and
CRITICAL is filtered before confidence is even read.
"""

from __future__ import annotations

from datetime import timedelta

from solarops.decision.domain.confidence import ConfidenceBand
from solarops.execution.domain.approval_request import ApprovalDecision, ApprovalRequest
from solarops.execution.domain.command import Command
from solarops.execution.domain.ports import ApprovalRequestRepository
from solarops.shared_kernel import ApprovalOutcome, ApprovalRequestId, Clock

DEFAULT_APPROVAL_TIMEOUT = timedelta(minutes=30)

__all__ = ["ApprovalEngine", "DEFAULT_APPROVAL_TIMEOUT"]


class ApprovalEngine:
    def __init__(
        self,
        approval_repository: ApprovalRequestRepository,
        clock: Clock,
        approval_timeout: timedelta = DEFAULT_APPROVAL_TIMEOUT,
    ) -> None:
        self._approval_repository = approval_repository
        self._clock = clock
        self._approval_timeout = approval_timeout

    def route(
        self, command: Command, *, confidence_band: ConfidenceBand = ConfidenceBand.MEDIUM
    ) -> ApprovalRequest | None:
        assert command.risk_assessment is not None, "route() requires apply_risk_assessment() first"
        level = command.risk_assessment.level

        if not level.is_auto_executable and not level.requires_manual_approval:
            # CRITICAL (or anything else outside LOW/MEDIUM/HIGH) — checked
            # before confidence is read at all, so a Low confidence_band can
            # never turn this into an approval request instead of the raise.
            raise ValueError(f"ApprovalEngine reached with an unexpected risk level: {level}")

        requires_approval = level.requires_manual_approval or confidence_band is ConfidenceBand.LOW
        if requires_approval:
            now = self._clock.now()
            request = ApprovalRequest(
                approval_request_id=ApprovalRequestId.generate(),
                command_id=command.command_id,
                site_id=command.site_id,
                risk_level=level,
                requested_at=now,
                timeout_at=now + self._approval_timeout,
            )
            self._approval_repository.save(request)
            command.await_approval()
            return request

        command.auto_approve()  # LOW/MEDIUM risk, and confidence isn't Low
        return None

    def decide(
        self, request: ApprovalRequest, command: Command, decision: ApprovalDecision
    ) -> None:
        request.decide(decision)
        self._approval_repository.save(request)
        if decision.outcome in (ApprovalOutcome.APPROVED, ApprovalOutcome.MODIFIED):
            command.approve(decision)
        else:
            command.reject_by_operator(decision)
