from datetime import UTC, datetime

import pytest

from solarops.decision.domain.confidence import ConfidenceBand
from solarops.decision.domain.recommendation import Recommendation
from solarops.execution.application.approval_engine import ApprovalEngine
from solarops.execution.application.command_planner import CommandPlanner
from solarops.execution.application.execution_manager import ExecutionManager
from solarops.execution.application.execution_pipeline import ExecutionPipeline
from solarops.execution.application.verification_service import VerificationService
from solarops.execution.domain.approval_request import ApprovalDecision
from solarops.execution.infrastructure.in_memory_approval_request_repository import (
    InMemoryApprovalRequestRepository,
)
from solarops.execution.infrastructure.in_memory_audit_log import InMemoryAuditLog
from solarops.execution.infrastructure.in_memory_command_repository import InMemoryCommandRepository
from solarops.safety.application.policy_validator import PolicyValidator
from solarops.safety.application.risk_assessor import RiskAssessor
from solarops.safety.application.safety_validator import SafetyValidator
from solarops.safety.domain.policy import Policy
from solarops.safety.domain.safety_limits import SafetyLimits
from solarops.safety.infrastructure.in_memory_policy_repository import InMemoryPolicyRepository
from solarops.safety.infrastructure.static_safety_limits_provider import StaticSafetyLimitsProvider
from solarops.shared_kernel import (
    ActionType,
    ApprovalOutcome,
    BatteryMode,
    CommandStatus,
    DuplicateCommandError,
    ExecutionOutcome,
    FixedClock,
    PolicyId,
    Power,
    RecommendationId,
    SiteId,
    StateOfCharge,
    Temperature,
)
from solarops.telemetry.application.state_manager import StateManager
from solarops.telemetry.domain.energy_state import EnergyState
from solarops.telemetry.infrastructure.in_memory_state_store import InMemoryStateStore

from ...telemetry.domain.test_telemetry import make_telemetry

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)
SITE_ID = SiteId("SITE-1")


class ScriptedHardwareInterface:
    """Always reports the given outcome without touching the state store —
    proves verification independently confirms reality rather than trusting
    the hardware's own claim of success."""

    def __init__(self, outcome: ExecutionOutcome = ExecutionOutcome.SUCCESS) -> None:
        self._outcome = outcome
        self.calls = []

    def send(self, *, asset_id, action, params):
        self.calls.append((asset_id, action, dict(params)))
        return self._outcome


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


def make_limits(**overrides) -> SafetyLimits:
    defaults = dict(
        battery_min_soc=StateOfCharge(10.0),
        battery_max_soc=StateOfCharge(95.0),
        battery_max_temp=Temperature(45.0),
        battery_max_charge_power=Power(50.0),
        battery_max_discharge_power=Power(50.0),
        inverter_max_power=Power(120.0),
    )
    defaults.update(overrides)
    return SafetyLimits(**defaults)


def make_recommendation(**overrides) -> Recommendation:
    defaults = dict(
        recommendation_id=RecommendationId.generate(),
        site_id=SITE_ID,
        action=ActionType.CHARGE_BATTERY,
        params={"power_kw": 20.0},
        confidence=0.9,
        expected_benefit="x",
        reason="y",
        generated_at=NOW,
    )
    defaults.update(overrides)
    return Recommendation(**defaults)


def make_state(*, any_asset_offline: bool = False, **overrides) -> EnergyState:
    telemetry = make_telemetry(site_id=SITE_ID, **overrides)
    return EnergyState.from_telemetry(telemetry, any_asset_offline=any_asset_offline)


class Rig:
    """Everything a pipeline needs, wired once, with the pieces a test wants
    to poke (policy, state store, hardware) exposed directly."""

    def __init__(
        self,
        *,
        policy: Policy | None = None,
        limits: SafetyLimits | None = None,
        state: EnergyState | None = None,
        seed_state: bool = True,
        hardware_outcome: ExecutionOutcome = ExecutionOutcome.SUCCESS,
    ):
        clock = FixedClock(NOW)
        self.clock = clock

        self.policy_repository = InMemoryPolicyRepository()
        if policy is not None:
            self.policy_repository.save(policy)
        else:
            self.policy_repository.save(make_policy())

        self.limits_provider = StaticSafetyLimitsProvider(limits or make_limits())

        self.state_store = InMemoryStateStore()
        if seed_state:
            self.state_store.set(state if state is not None else make_state())

        policy_validator = PolicyValidator(self.policy_repository, clock)
        safety_validator = SafetyValidator(self.limits_provider, self.state_store, clock)
        risk_assessor = RiskAssessor(clock)
        command_planner = CommandPlanner(clock)
        self.approval_repository = InMemoryApprovalRequestRepository()
        approval_engine = ApprovalEngine(self.approval_repository, clock)
        self.hardware = ScriptedHardwareInterface(hardware_outcome)
        execution_manager = ExecutionManager(self.hardware, clock)
        state_manager = StateManager(self.state_store)
        verification_service = VerificationService(state_manager, clock)
        self.command_repository = InMemoryCommandRepository()
        self.audit_log = InMemoryAuditLog()

        self.pipeline = ExecutionPipeline(
            command_planner=command_planner,
            policy_validator=policy_validator,
            safety_validator=safety_validator,
            risk_assessor=risk_assessor,
            approval_engine=approval_engine,
            execution_manager=execution_manager,
            verification_service=verification_service,
            command_repository=self.command_repository,
            approval_repository=self.approval_repository,
            audit_log=self.audit_log,
            state_store=self.state_store,
            policy_repository=self.policy_repository,
            safety_limits_provider=self.limits_provider,
            clock=clock,
        )


# --- happy path ---


def test_happy_path_low_risk_command_completes_with_verification():
    rig = Rig(state=make_state(battery_soc=StateOfCharge(50.0), battery_mode=BatteryMode.CHARGING))
    command = rig.pipeline.run(make_recommendation())

    assert command.status is CommandStatus.COMPLETED
    assert command.status.is_success
    assert command.verification_result is not None
    assert command.verification_result.passed is True
    assert len(rig.hardware.calls) == 1
    assert len(rig.audit_log.all()) > 5  # a full trail of events was written


# --- gate failures terminate correctly ---


def test_policy_gate_rejects_charging_during_maintenance():
    rig = Rig(policy=make_policy(maintenance_mode=True))
    command = rig.pipeline.run(make_recommendation(action=ActionType.CHARGE_BATTERY))
    assert command.status is CommandStatus.REJECTED_BY_POLICY
    assert len(rig.hardware.calls) == 0


def test_safety_gate_blocks_when_battery_already_at_max_soc():
    rig = Rig(state=make_state(battery_soc=StateOfCharge(95.0)))
    command = rig.pipeline.run(make_recommendation(action=ActionType.CHARGE_BATTERY))
    assert command.status is CommandStatus.BLOCKED_BY_SAFETY
    assert len(rig.hardware.calls) == 0  # never reaches the twin


def test_fail_safe_when_state_store_has_no_reading_at_all():
    # Policy validation doesn't need EnergyState, so it passes; the fail-safe
    # trips at the safety gate (SafetyValidator can't read a current state),
    # and the pipeline must reject rather than raise FailSafeTriggered out of
    # run() or silently proceed.
    rig = Rig(seed_state=False)
    command = rig.pipeline.run(make_recommendation())
    assert command.status is CommandStatus.BLOCKED_BY_SAFETY
    assert command.safety_assessment is not None
    assert command.safety_assessment.passed is False
    assert "fail-safe" in command.safety_assessment.failed_checks[0]
    assert len(rig.hardware.calls) == 0


def test_critical_risk_is_rejected_before_dispatch():
    # any_asset_offline is CRITICAL per RiskAssessor but isn't one of
    # SafetyValidator's own checks, so this genuinely reaches the risk gate
    # (unlike e.g. grid outage on a grid action, which SafetyValidator itself
    # already blocks — proving the risk gate is a real, separate layer).
    rig = Rig(state=make_state(any_asset_offline=True))
    command = rig.pipeline.run(make_recommendation())
    assert command.status is CommandStatus.REJECTED_BY_RISK
    assert len(rig.hardware.calls) == 0


# --- idempotency ---


def test_duplicate_recommendation_is_rejected():
    rig = Rig()
    recommendation = make_recommendation()
    rig.pipeline.run(recommendation)
    with pytest.raises(DuplicateCommandError):
        rig.pipeline.run(recommendation)


# --- approval pause / resume ---


def test_high_risk_pauses_then_approve_resumes_to_completion():
    rig = Rig()
    recommendation = make_recommendation(params={"power_kw": 45.0})  # large swing -> HIGH
    command = rig.pipeline.run(recommendation)
    assert command.status is CommandStatus.AWAITING_APPROVAL
    assert len(rig.hardware.calls) == 0

    decision = ApprovalDecision(outcome=ApprovalOutcome.APPROVED, decided_at=NOW)
    resumed = rig.pipeline.resume_after_approval(command, decision)
    assert resumed.status is CommandStatus.COMPLETED


def test_high_risk_reject_terminates_without_dispatch():
    rig = Rig()
    recommendation = make_recommendation(params={"power_kw": 45.0})
    command = rig.pipeline.run(recommendation)
    decision = ApprovalDecision(outcome=ApprovalOutcome.REJECTED, decided_at=NOW)
    resumed = rig.pipeline.resume_after_approval(command, decision)
    assert resumed.status is CommandStatus.REJECTED_BY_OPERATOR
    assert len(rig.hardware.calls) == 0


def test_high_risk_modify_dispatches_with_modified_params():
    rig = Rig()
    recommendation = make_recommendation(params={"power_kw": 45.0})
    command = rig.pipeline.run(recommendation)
    decision = ApprovalDecision(
        outcome=ApprovalOutcome.MODIFIED, decided_at=NOW, modified_params={"power_kw": 10.0}
    )
    resumed = rig.pipeline.resume_after_approval(command, decision)
    assert resumed.status is CommandStatus.COMPLETED
    assert rig.hardware.calls[0][2] == {"power_kw": 10.0}


# --- mandatory verification ---


def test_acknowledged_but_unchanged_telemetry_fails_verification_not_completed():
    # The hardware claims SUCCESS but the state store's battery_mode never
    # actually changes to CHARGING — verification must catch that.
    rig = Rig(state=make_state(battery_mode=BatteryMode.IDLE))
    command = rig.pipeline.run(make_recommendation())

    assert command.status is CommandStatus.VERIFICATION_FAILED
    assert command.status is not CommandStatus.COMPLETED
    assert command.execution_result is not None
    assert command.execution_result.outcome.is_success  # hardware said SUCCESS...
    assert command.verification_result.passed is False  # ...but verification disagreed


# --- Phase 6d: confidence-driven escalation, end to end ---


def test_low_confidence_pauses_a_recommendation_that_would_normally_auto_execute():
    # Same scenario as the happy path (normally COMPLETED, no approval) —
    # only the recommendation's confidence_band changes, to Low.
    rig = Rig(state=make_state(battery_soc=StateOfCharge(50.0), battery_mode=BatteryMode.CHARGING))
    recommendation = make_recommendation(confidence_band=ConfidenceBand.LOW)
    command = rig.pipeline.run(recommendation)

    assert command.status is CommandStatus.AWAITING_APPROVAL
    assert len(rig.hardware.calls) == 0


def test_high_risk_approval_requirement_is_unchanged_by_confidence_band():
    for band in (ConfidenceBand.HIGH, ConfidenceBand.MEDIUM, ConfidenceBand.LOW):
        rig = Rig()
        recommendation = make_recommendation(params={"power_kw": 45.0}, confidence_band=band)
        command = rig.pipeline.run(recommendation)
        assert command.status is CommandStatus.AWAITING_APPROVAL


def test_critical_risk_still_auto_rejects_regardless_of_confidence_band():
    rig = Rig(state=make_state(any_asset_offline=True))
    recommendation = make_recommendation(confidence_band=ConfidenceBand.LOW)
    command = rig.pipeline.run(recommendation)
    assert command.status is CommandStatus.REJECTED_BY_RISK
    assert len(rig.hardware.calls) == 0
