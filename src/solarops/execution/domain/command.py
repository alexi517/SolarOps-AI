"""Command — aggregate root, owns the full CESF §7 lifecycle state machine (Doc 8 §6.5, §7).

Every transition is a method that validates the current status first and
raises ``InvalidStateTransition`` otherwise — there is no code path that sets
``status`` directly, and no code path that moves backward or skips a gate.
This is what makes "100% of unsafe commands blocked" and "verification is
mandatory" structural properties of the aggregate rather than scattered
``if`` checks a caller could forget (Doc 8 §7 invariants 1-6).

Command does **not** construct or emit domain events itself — that's
``ExecutionPipeline``'s job (application layer), which has the full context
(the actual ``PolicyResult``/``SafetyAssessment``/etc.) to build meaningful
event payloads. Command's only concern is: is this transition legal, and what
gate outcome does it carry.
"""

from __future__ import annotations

from datetime import datetime

from solarops.execution.domain.approval_request import ApprovalDecision
from solarops.execution.domain.execution_result import ExecutionResult
from solarops.execution.domain.verification_result import VerificationResult
from solarops.safety.domain.policy_result import PolicyResult
from solarops.safety.domain.risk_assessment import RiskAssessment
from solarops.safety.domain.safety_assessment import SafetyAssessment
from solarops.shared_kernel import (
    ActionType,
    AssetId,
    CommandId,
    CommandStatus,
    InvalidStateTransition,
    RecommendationId,
    SiteId,
)

__all__ = ["Command"]

_DISPATCHABLE_STATUSES = frozenset({CommandStatus.AUTO_APPROVED, CommandStatus.APPROVED})


class Command:
    def __init__(
        self,
        *,
        command_id: CommandId,
        site_id: SiteId,
        asset_id: AssetId,
        recommendation_id: RecommendationId,
        action: ActionType,
        params: dict,
        idempotency_key: str,
        trace_id: str,
        created_at: datetime,
    ) -> None:
        self._command_id = command_id
        self._site_id = site_id
        self._asset_id = asset_id
        self._recommendation_id = recommendation_id
        self._action = action
        self._params = dict(params)
        self._idempotency_key = idempotency_key
        self._trace_id = trace_id
        self._created_at = created_at

        self._status = CommandStatus.CREATED
        self._policy_result: PolicyResult | None = None
        self._safety_assessment: SafetyAssessment | None = None
        self._risk_assessment: RiskAssessment | None = None
        self._approval_decision: ApprovalDecision | None = None
        self._execution_result: ExecutionResult | None = None
        self._verification_result: VerificationResult | None = None

    # --- identity / plan (read-only) ---

    @property
    def command_id(self) -> CommandId:
        return self._command_id

    @property
    def site_id(self) -> SiteId:
        return self._site_id

    @property
    def asset_id(self) -> AssetId:
        return self._asset_id

    @property
    def recommendation_id(self) -> RecommendationId:
        return self._recommendation_id

    @property
    def action(self) -> ActionType:
        return self._action

    @property
    def params(self) -> dict:
        return dict(self._params)

    @property
    def idempotency_key(self) -> str:
        return self._idempotency_key

    @property
    def trace_id(self) -> str:
        return self._trace_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    # --- gate outcomes (read-only) ---

    @property
    def status(self) -> CommandStatus:
        return self._status

    @property
    def policy_result(self) -> PolicyResult | None:
        return self._policy_result

    @property
    def safety_assessment(self) -> SafetyAssessment | None:
        return self._safety_assessment

    @property
    def risk_assessment(self) -> RiskAssessment | None:
        return self._risk_assessment

    @property
    def approval_decision(self) -> ApprovalDecision | None:
        return self._approval_decision

    @property
    def execution_result(self) -> ExecutionResult | None:
        return self._execution_result

    @property
    def verification_result(self) -> VerificationResult | None:
        return self._verification_result

    # --- construction ---

    @classmethod
    def create(
        cls,
        *,
        site_id: SiteId,
        asset_id: AssetId,
        recommendation_id: RecommendationId,
        action: ActionType,
        params: dict,
        idempotency_key: str,
        trace_id: str,
        created_at: datetime,
    ) -> Command:
        """CREATED -> PLANNED, folded into one step: a Command only ever
        becomes visible to the rest of the pipeline already planned."""
        command = cls(
            command_id=CommandId.generate(),
            site_id=site_id,
            asset_id=asset_id,
            recommendation_id=recommendation_id,
            action=action,
            params=params,
            idempotency_key=idempotency_key,
            trace_id=trace_id,
            created_at=created_at,
        )
        command._status = CommandStatus.PLANNED
        return command

    # --- transitions ---

    def _transition(
        self, expected: CommandStatus | frozenset[CommandStatus], new: CommandStatus
    ) -> None:
        allowed = {expected} if isinstance(expected, CommandStatus) else expected
        if self._status not in allowed:
            raise InvalidStateTransition(current=self._status, attempted=new, entity="Command")
        self._status = new

    def apply_policy_result(self, result: PolicyResult) -> None:
        self._policy_result = result
        new = CommandStatus.POLICY_VALIDATED if result.passed else CommandStatus.REJECTED_BY_POLICY
        self._transition(CommandStatus.PLANNED, new)

    def apply_safety_assessment(self, assessment: SafetyAssessment) -> None:
        self._safety_assessment = assessment
        new = (
            CommandStatus.SAFETY_VALIDATED if assessment.passed else CommandStatus.BLOCKED_BY_SAFETY
        )
        self._transition(CommandStatus.POLICY_VALIDATED, new)

    def apply_risk_assessment(self, assessment: RiskAssessment) -> None:
        self._risk_assessment = assessment
        self._transition(CommandStatus.SAFETY_VALIDATED, CommandStatus.RISK_ASSESSED)

    def reject_by_risk(self) -> None:
        """CRITICAL risk -> auto-reject. Never dispatchable (Doc 8 §7 invariant 2)."""
        self._transition(CommandStatus.RISK_ASSESSED, CommandStatus.REJECTED_BY_RISK)

    def auto_approve(self) -> None:
        self._transition(CommandStatus.RISK_ASSESSED, CommandStatus.AUTO_APPROVED)

    def await_approval(self) -> None:
        self._transition(CommandStatus.RISK_ASSESSED, CommandStatus.AWAITING_APPROVAL)

    def approve(self, decision: ApprovalDecision) -> None:
        self._approval_decision = decision
        self._transition(CommandStatus.AWAITING_APPROVAL, CommandStatus.APPROVED)

    def reject_by_operator(self, decision: ApprovalDecision) -> None:
        self._approval_decision = decision
        self._transition(CommandStatus.AWAITING_APPROVAL, CommandStatus.REJECTED_BY_OPERATOR)

    def expire_approval(self, decision: ApprovalDecision) -> None:
        self._approval_decision = decision
        self._transition(CommandStatus.AWAITING_APPROVAL, CommandStatus.TIMED_OUT)

    def dispatch(self) -> None:
        """Doc 8 §7 invariant 1: only reachable via AUTO_APPROVED/APPROVED,
        which themselves are only reachable after policy + safety passed."""
        self._transition(_DISPATCHABLE_STATUSES, CommandStatus.DISPATCHED)

    def mark_dispatch_failed(self) -> None:
        self._transition(CommandStatus.DISPATCHED, CommandStatus.DISPATCH_FAILED)

    def acknowledge(self) -> None:
        self._transition(CommandStatus.DISPATCHED, CommandStatus.ACKNOWLEDGED)

    def mark_executed(self, result: ExecutionResult) -> None:
        self._execution_result = result
        self._transition(CommandStatus.ACKNOWLEDGED, CommandStatus.EXECUTED)

    def mark_execution_failed(self, result: ExecutionResult) -> None:
        self._execution_result = result
        self._transition(CommandStatus.ACKNOWLEDGED, CommandStatus.EXECUTION_FAILED)

    def timeout_execution(self, result: ExecutionResult) -> None:
        self._execution_result = result
        self._transition(CommandStatus.ACKNOWLEDGED, CommandStatus.TIMED_OUT)

    def verify(self, result: VerificationResult) -> None:
        self._verification_result = result
        new = CommandStatus.VERIFIED if result.passed else CommandStatus.VERIFICATION_FAILED
        self._transition(CommandStatus.EXECUTED, new)

    def complete(self) -> None:
        """ADR-011: acknowledgement alone never completes a command. This is
        only reachable from VERIFIED, which itself only exists because
        verify() saw a passing VerificationResult — structurally impossible
        to reach COMPLETED without one (Doc 8 §7 invariant 4)."""
        self._transition(CommandStatus.VERIFIED, CommandStatus.COMPLETED)

    def cancel(self) -> None:
        if self._status.is_terminal:
            raise InvalidStateTransition(
                current=self._status, attempted=CommandStatus.CANCELLED, entity="Command"
            )
        self._status = CommandStatus.CANCELLED
