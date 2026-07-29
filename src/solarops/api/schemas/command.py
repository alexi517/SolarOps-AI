"""Command -> JSON — summary for lists, full detail (every gate outcome) for
GET /commands/{id}."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from solarops.execution.domain.command import Command

__all__ = [
    "PolicyResultResponse",
    "SafetyAssessmentResponse",
    "RiskAssessmentResponse",
    "ApprovalDecisionResponse",
    "ExecutionResultResponse",
    "VerificationResultResponse",
    "CommandSummaryResponse",
    "CommandDetailResponse",
]


class PolicyResultResponse(BaseModel):
    passed: bool
    violations: list[str]
    evaluated_at: datetime


class SafetyAssessmentResponse(BaseModel):
    passed: bool
    failed_checks: list[str]
    evaluated_at: datetime


class RiskAssessmentResponse(BaseModel):
    level: str
    factors: list[str]
    assessed_at: datetime


class ApprovalDecisionResponse(BaseModel):
    outcome: str
    decided_at: datetime
    operator_id: str | None
    modified_params: dict | None
    reason: str


class ExecutionResultResponse(BaseModel):
    outcome: str
    dispatched_at: datetime
    acknowledged_at: datetime | None
    retry_count: int
    detail: str


class VerificationResultResponse(BaseModel):
    passed: bool
    expected: str
    observed: str
    verified_at: datetime


class CommandSummaryResponse(BaseModel):
    command_id: str
    site_id: str
    asset_id: str
    action: str
    status: str
    created_at: datetime

    @classmethod
    def from_domain(cls, command: Command) -> CommandSummaryResponse:
        return cls(
            command_id=str(command.command_id),
            site_id=str(command.site_id),
            asset_id=str(command.asset_id),
            action=command.action.value,
            status=command.status.value,
            created_at=command.created_at,
        )


class CommandDetailResponse(CommandSummaryResponse):
    recommendation_id: str
    params: dict
    idempotency_key: str
    trace_id: str
    policy_result: PolicyResultResponse | None
    safety_assessment: SafetyAssessmentResponse | None
    risk_assessment: RiskAssessmentResponse | None
    approval_decision: ApprovalDecisionResponse | None
    execution_result: ExecutionResultResponse | None
    verification_result: VerificationResultResponse | None

    @classmethod
    def from_domain(cls, command: Command) -> CommandDetailResponse:
        policy_result = command.policy_result
        safety_assessment = command.safety_assessment
        risk_assessment = command.risk_assessment
        approval_decision = command.approval_decision
        execution_result = command.execution_result
        verification_result = command.verification_result

        return cls(
            command_id=str(command.command_id),
            site_id=str(command.site_id),
            asset_id=str(command.asset_id),
            action=command.action.value,
            status=command.status.value,
            created_at=command.created_at,
            recommendation_id=str(command.recommendation_id),
            params=command.params,
            idempotency_key=command.idempotency_key,
            trace_id=command.trace_id,
            policy_result=(
                PolicyResultResponse(
                    passed=policy_result.passed,
                    violations=list(policy_result.violations),
                    evaluated_at=policy_result.evaluated_at,
                )
                if policy_result is not None
                else None
            ),
            safety_assessment=(
                SafetyAssessmentResponse(
                    passed=safety_assessment.passed,
                    failed_checks=list(safety_assessment.failed_checks),
                    evaluated_at=safety_assessment.evaluated_at,
                )
                if safety_assessment is not None
                else None
            ),
            risk_assessment=(
                RiskAssessmentResponse(
                    level=risk_assessment.level.name,
                    factors=list(risk_assessment.factors),
                    assessed_at=risk_assessment.assessed_at,
                )
                if risk_assessment is not None
                else None
            ),
            approval_decision=(
                ApprovalDecisionResponse(
                    outcome=approval_decision.outcome.value,
                    decided_at=approval_decision.decided_at,
                    operator_id=(
                        str(approval_decision.operator_id)
                        if approval_decision.operator_id
                        else None
                    ),
                    modified_params=approval_decision.modified_params,
                    reason=approval_decision.reason,
                )
                if approval_decision is not None
                else None
            ),
            execution_result=(
                ExecutionResultResponse(
                    outcome=execution_result.outcome.value,
                    dispatched_at=execution_result.dispatched_at,
                    acknowledged_at=execution_result.acknowledged_at,
                    retry_count=execution_result.retry_count,
                    detail=execution_result.detail,
                )
                if execution_result is not None
                else None
            ),
            verification_result=(
                VerificationResultResponse(
                    passed=verification_result.passed,
                    expected=verification_result.expected,
                    observed=verification_result.observed,
                    verified_at=verification_result.verified_at,
                )
                if verification_result is not None
                else None
            ),
        )
