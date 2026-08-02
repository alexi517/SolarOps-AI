"""ExecutionPipeline — orchestrates the full CESF §3 flow (Doc 8 §6.5).

recommendation -> plan -> policy -> safety -> risk -> approval -> dispatch ->
verify -> audit -> state. Terminates safely at any gate failure (§13). Every
transition writes an ``EventEnvelope`` to the audit log (gap #4 in the Phase 5
plan — a real ``AuditEntry`` belongs to the Observability context, Phase 7;
the shared kernel's existing envelope is the persisted-header type built for
exactly this in the meantime).

``Command`` itself never constructs events (see its module docstring) — this
class is the one place that does, because it's the one place with the full
context (the actual gate-result objects) to build them meaningfully.

Phase 7c: ``_audit()`` is also the one place every domain event this pipeline
emits already passes through, so it's the metrics-recording seam too — see
``_record_metric()``. ``metrics`` is typed as Execution's own
``ExecutionMetricsRecorder`` Protocol (``execution/domain/ports.py``) —
Observability is forbidden to every context by every import-linter contract,
so this module never imports it; the real ``prometheus_client``-backed
implementation is constructed and injected by ``platform``'s composition
root, which is already allowed to import both.
"""

from __future__ import annotations

from solarops.decision.domain.recommendation import Recommendation
from solarops.execution.application.approval_engine import ApprovalEngine
from solarops.execution.application.command_intent_mapper import to_command_intent
from solarops.execution.application.command_planner import CommandPlanner
from solarops.execution.application.execution_manager import ExecutionManager
from solarops.execution.application.verification_service import VerificationService
from solarops.execution.domain.approval_request import ApprovalDecision
from solarops.execution.domain.command import Command
from solarops.execution.domain.events import (
    ApprovalRequested,
    CommandAcknowledged,
    CommandApproved,
    CommandCompleted,
    CommandCreated,
    CommandDispatched,
    CommandExecuted,
    CommandFailed,
    CommandRejected,
    CommandTimedOut,
    CommandValidated,
    ExecutionVerified,
)
from solarops.execution.domain.events import VerificationFailed as VerificationFailedEvent
from solarops.execution.domain.ports import (
    ApprovalNotifier,
    ApprovalRequestRepository,
    CommandRepository,
    ExecutionMetricsRecorder,
)
from solarops.safety.application.policy_validator import PolicyValidator
from solarops.safety.application.risk_assessor import RiskAssessor
from solarops.safety.application.safety_validator import SafetyValidator
from solarops.safety.domain.events import CommandBlockedBySafety, RiskAssessed
from solarops.safety.domain.ports import PolicyRepository, SafetyLimitsProvider
from solarops.safety.domain.risk_assessment import RiskAssessment
from solarops.safety.domain.safety_assessment import SafetyAssessment
from solarops.shared_kernel import (
    AssetOperatingMode,
    Clock,
    CommandStatus,
    DomainEvent,
    DuplicateCommandError,
    FailSafeTriggered,
    RiskLevel,
)
from solarops.telemetry.domain.ports import StateStore

__all__ = ["ExecutionPipeline"]


def _rejection_reason_category(reason: str) -> str:
    """Categorises the free-text ``CommandRejected.reason`` this pipeline
    itself writes (see ``_reject()``'s four call sites in ``run()``/
    ``resume_after_approval()``) into a small, stable metric label set."""
    if reason == "operator rejected":
        return "operator"
    if reason == "policy violation":
        return "policy"
    if reason.startswith("fail-safe:"):
        return "fail_safe"
    if reason == "risk level CRITICAL" or reason.startswith("cannot assess risk"):
        return "risk_critical"
    return "other"


class ExecutionPipeline:
    def __init__(
        self,
        *,
        command_planner: CommandPlanner,
        policy_validator: PolicyValidator,
        safety_validator: SafetyValidator,
        risk_assessor: RiskAssessor,
        approval_engine: ApprovalEngine,
        execution_manager: ExecutionManager,
        verification_service: VerificationService,
        command_repository: CommandRepository,
        approval_repository: ApprovalRequestRepository,
        audit_log,
        state_store: StateStore,
        policy_repository: PolicyRepository,
        safety_limits_provider: SafetyLimitsProvider,
        clock: Clock,
        telemetry_refresh=None,
        metrics: ExecutionMetricsRecorder | None = None,
        notifier: ApprovalNotifier | None = None,
    ) -> None:
        # Optional no-arg callable invoked right before verification — pulls a
        # fresh telemetry reading into the StateStore so verification doesn't
        # compare against the pre-command snapshot. In a running system,
        # telemetry ingestion happens continuously on its own cycle and this
        # would be unnecessary; for a synchronous pipeline/script driving a
        # single twin, nothing else advances telemetry between dispatch and
        # verify unless this is provided.
        self._telemetry_refresh = telemetry_refresh
        # Optional (Phase 7c) — None means "record nothing", same shape as
        # telemetry_refresh above. Every existing caller that doesn't pass
        # one keeps working unchanged.
        self._metrics = metrics
        # Optional — None means "notify nobody," same shape as metrics above.
        self._notifier = notifier
        self._command_planner = command_planner
        self._policy_validator = policy_validator
        self._safety_validator = safety_validator
        self._risk_assessor = risk_assessor
        self._approval_engine = approval_engine
        self._execution_manager = execution_manager
        self._verification_service = verification_service
        self._command_repository = command_repository
        self._approval_repository = approval_repository
        self._audit_log = audit_log
        self._state_store = state_store
        self._policy_repository = policy_repository
        self._safety_limits_provider = safety_limits_provider
        self._clock = clock

    def run(
        self,
        recommendation: Recommendation,
        *,
        asset_operating_mode: AssetOperatingMode | None = None,
    ) -> Command:
        idempotency_key = f"idem-{recommendation.recommendation_id}"
        if self._command_repository.get_by_idempotency_key(idempotency_key) is not None:
            raise DuplicateCommandError(idempotency_key)

        command, created_event = self._command_planner.plan(recommendation)
        self._audit(created_event)
        self._command_repository.save(command)

        intent = to_command_intent(command, asset_operating_mode=asset_operating_mode)

        # --- POLICY GATE ---
        policy_result, policy_events = self._policy_validator.validate(intent)
        for event in policy_events:
            self._audit(event)
        command.apply_policy_result(policy_result)
        self._command_repository.save(command)
        if not policy_result.passed:
            self._reject(command, "policy violation")
            return command
        self._audit(self._event(CommandValidated, command))

        # --- SAFETY GATE (fail-safe, ADR-012) ---
        try:
            safety_assessment = self._safety_validator.validate(intent)
        except FailSafeTriggered as exc:
            safety_assessment = SafetyAssessment(
                passed=False, failed_checks=(f"fail-safe: {exc}",), evaluated_at=self._clock.now()
            )
            command.apply_safety_assessment(safety_assessment)
            self._command_repository.save(command)
            self._reject(command, f"fail-safe: {exc}")
            return command
        command.apply_safety_assessment(safety_assessment)
        self._command_repository.save(command)
        if not safety_assessment.passed:
            self._audit(
                CommandBlockedBySafety(
                    aggregate_id=str(command.command_id),
                    aggregate_type="Command",
                    failed_checks=safety_assessment.failed_checks,
                )
            )
            return command

        # --- RISK GATE ---
        state = self._state_store.get(command.site_id)
        policy = self._policy_repository.get_current(command.site_id)
        limits = self._safety_limits_provider.get_limits(command.site_id)
        if state is None or policy is None or limits is None:
            reason = "cannot assess risk: current state, policy, or limits unavailable"
            unavailable = RiskAssessment(
                level=RiskLevel.CRITICAL, factors=(reason,), assessed_at=self._clock.now()
            )
            command.apply_risk_assessment(unavailable)
            command.reject_by_risk()
            self._command_repository.save(command)
            self._reject(command, reason)
            return command

        risk_assessment = self._risk_assessor.assess(
            intent, state, policy, limits, safety_assessment
        )
        command.apply_risk_assessment(risk_assessment)
        self._audit(
            RiskAssessed(
                aggregate_id=str(command.command_id),
                aggregate_type="Command",
                level=risk_assessment.level,
                factors=risk_assessment.factors,
            )
        )
        self._command_repository.save(command)

        if risk_assessment.level.is_auto_rejected:
            command.reject_by_risk()
            self._command_repository.save(command)
            self._reject(command, "risk level CRITICAL")
            return command

        approval_request = self._approval_engine.route(
            command, confidence_band=recommendation.confidence_band
        )
        self._command_repository.save(command)
        if approval_request is not None:
            self._audit(
                ApprovalRequested(
                    aggregate_id=str(command.command_id),
                    aggregate_type="Command",
                    approval_request_id=str(approval_request.approval_request_id),
                )
            )
            if self._notifier is not None:
                self._notifier.notify_approval_needed(command)
            return command  # PAUSED — resume_after_approval() continues this

        self._audit(
            CommandApproved(
                aggregate_id=str(command.command_id), aggregate_type="Command", operator_id="AUTO"
            )
        )
        return self._dispatch_and_verify(command)

    def resume_after_approval(self, command: Command, decision: ApprovalDecision) -> Command:
        request = self._approval_repository.get_pending_for_command(command.command_id)
        if request is None:
            raise ValueError(f"no pending approval request for {command.command_id}")

        self._approval_engine.decide(request, command, decision)
        self._command_repository.save(command)

        if self._metrics is not None:
            wait_seconds = (decision.decided_at - request.requested_at).total_seconds()
            self._metrics.approval_wait_time(wait_seconds)

        if command.status is CommandStatus.REJECTED_BY_OPERATOR:
            self._reject(command, "operator rejected")
            return command

        operator_label = str(decision.operator_id) if decision.operator_id else "UNKNOWN"
        self._audit(
            CommandApproved(
                aggregate_id=str(command.command_id),
                aggregate_type="Command",
                operator_id=operator_label,
            )
        )
        return self._dispatch_and_verify(command)

    def _dispatch_and_verify(self, command: Command) -> Command:
        result = self._execution_manager.dispatch(command)
        self._command_repository.save(command)

        if self._metrics is not None:
            self._metrics.retry_count(result.retry_count)
            if result.acknowledged_at is not None:
                latency = (result.acknowledged_at - result.dispatched_at).total_seconds()
                self._metrics.execution_latency(latency)

        if command.status in (CommandStatus.DISPATCH_FAILED, CommandStatus.EXECUTION_FAILED):
            self._audit(
                CommandFailed(
                    aggregate_id=str(command.command_id),
                    aggregate_type="Command",
                    reason=result.detail or "execution failed",
                )
            )
            return command
        if command.status is CommandStatus.TIMED_OUT:
            self._audit(
                CommandTimedOut(
                    aggregate_id=str(command.command_id),
                    aggregate_type="Command",
                    stage="execution",
                )
            )
            return command

        # ExecutionManager performed DISPATCHED -> ACKNOWLEDGED -> EXECUTED
        # internally (see its own module); this is the audit trail for that
        # sequence, written once the pipeline observes the final status.
        self._audit(self._event(CommandDispatched, command))
        self._audit(self._event(CommandAcknowledged, command))
        self._audit(
            CommandExecuted(
                aggregate_id=str(command.command_id),
                aggregate_type="Command",
                outcome=result.outcome,
            )
        )

        if self._telemetry_refresh is not None:
            self._telemetry_refresh()
        verification = self._verification_service.verify(command)
        command.verify(verification)
        self._command_repository.save(command)

        if not verification.passed:
            self._audit(
                VerificationFailedEvent(
                    aggregate_id=str(command.command_id),
                    aggregate_type="Command",
                    expected=verification.expected,
                    observed=verification.observed,
                )
            )
            return command

        self._audit(self._event(ExecutionVerified, command))
        command.complete()
        self._command_repository.save(command)
        self._audit(self._event(CommandCompleted, command))
        return command

    def _reject(self, command: Command, reason: str) -> None:
        self._audit(
            CommandRejected(
                aggregate_id=str(command.command_id), aggregate_type="Command", reason=reason
            )
        )

    @staticmethod
    def _event(event_cls: type[DomainEvent], command: Command) -> DomainEvent:
        return event_cls(aggregate_id=str(command.command_id), aggregate_type="Command")

    def _audit(self, event: DomainEvent) -> None:
        self._audit_log.append(event)
        if self._metrics is not None:
            self._record_metric(event)

    def _record_metric(self, event: DomainEvent) -> None:
        """Every domain event this pipeline emits already passes through
        ``_audit()`` — this is that same seam, not a second one."""
        if isinstance(event, CommandCreated):
            self._metrics.command_issued()
        elif isinstance(event, CommandBlockedBySafety):
            self._metrics.command_blocked_by_safety()
        elif isinstance(event, CommandRejected):
            self._metrics.command_rejected(_rejection_reason_category(event.reason))
        elif isinstance(event, ApprovalRequested):
            self._metrics.approval_required()
        elif isinstance(event, CommandApproved):
            if event.operator_id != "AUTO":
                self._metrics.approval_approved()
        elif isinstance(event, CommandFailed):
            self._metrics.command_failed()
        elif isinstance(event, CommandTimedOut):
            self._metrics.command_timed_out(event.stage)
        elif isinstance(event, VerificationFailedEvent):
            self._metrics.verification_failed()
        elif isinstance(event, CommandCompleted):
            self._metrics.command_completed()
