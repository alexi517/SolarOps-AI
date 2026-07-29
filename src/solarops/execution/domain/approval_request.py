"""ApprovalRequest — a separate aggregate root from Command (ADR-017, Doc 8 §6.5).

Human approval is asynchronous, long-lived, and has its own timeout lifecycle
— kept out of ``Command``'s consistency boundary so approval doesn't hold a
transaction open across a human decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from solarops.shared_kernel import (
    ApprovalOutcome,
    ApprovalRequestId,
    CommandId,
    InvalidStateTransition,
    OperatorId,
    RiskLevel,
    SiteId,
)

__all__ = ["ApprovalDecision", "ApprovalRequest"]


@dataclass(frozen=True, slots=True)
class ApprovalDecision:
    outcome: ApprovalOutcome  # APPROVED, REJECTED, MODIFIED, or EXPIRED
    decided_at: datetime
    operator_id: OperatorId | None = None  # None for a system-driven EXPIRED decision
    modified_params: dict | None = None  # set only for MODIFIED
    reason: str = ""


class ApprovalRequest:
    def __init__(
        self,
        *,
        approval_request_id: ApprovalRequestId,
        command_id: CommandId,
        site_id: SiteId,
        risk_level: RiskLevel,
        requested_at: datetime,
        timeout_at: datetime,
    ) -> None:
        self._approval_request_id = approval_request_id
        self._command_id = command_id
        self._site_id = site_id
        self._risk_level = risk_level
        self._requested_at = requested_at
        self._timeout_at = timeout_at
        self._decision: ApprovalDecision | None = None

    @property
    def approval_request_id(self) -> ApprovalRequestId:
        return self._approval_request_id

    @property
    def command_id(self) -> CommandId:
        return self._command_id

    @property
    def site_id(self) -> SiteId:
        return self._site_id

    @property
    def risk_level(self) -> RiskLevel:
        return self._risk_level

    @property
    def requested_at(self) -> datetime:
        return self._requested_at

    @property
    def timeout_at(self) -> datetime:
        return self._timeout_at

    @property
    def decision(self) -> ApprovalDecision | None:
        return self._decision

    @property
    def is_pending(self) -> bool:
        return self._decision is None

    def decide(self, decision: ApprovalDecision) -> None:
        if not self.is_pending:
            raise InvalidStateTransition(
                current=self._decision.outcome, attempted=decision.outcome, entity="ApprovalRequest"
            )
        self._decision = decision

    def expire(self, expired_at: datetime) -> None:
        if not self.is_pending:
            raise InvalidStateTransition(
                current=self._decision.outcome,
                attempted=ApprovalOutcome.EXPIRED,
                entity="ApprovalRequest",
            )
        self._decision = ApprovalDecision(outcome=ApprovalOutcome.EXPIRED, decided_at=expired_at)
