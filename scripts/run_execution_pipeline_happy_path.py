"""Smoke test: real EnergyState -> real RuleBasedOptimiser -> full pipeline ->
twin executes -> verified -> COMPLETED.

Every context built so far, in this order: Simulation (Phase 2) -> Telemetry
(Phase 3) -> Decision (Phase 4 stub, Phase 6c real engine) -> Safety +
Execution (Phase 5) -> platform composition root wiring it all to one real
Digital Twin. Proves the full thesis end to end: a real reading, reasoned
about by the brain, produces an explained recommendation that then runs
through Safety's independent gate before anything could act.
"""

from datetime import UTC, datetime

from solarops.decision.application.rule_based_optimiser import RuleBasedOptimiser
from solarops.decision.domain.decision_context import DecisionContext
from solarops.decision.infrastructure.config import RuleEngineConfig
from solarops.execution.application.approval_engine import ApprovalEngine
from solarops.execution.application.command_planner import CommandPlanner
from solarops.execution.application.execution_manager import ExecutionManager
from solarops.execution.application.execution_pipeline import ExecutionPipeline
from solarops.execution.application.verification_service import VerificationService
from solarops.execution.infrastructure.in_memory_approval_request_repository import (
    InMemoryApprovalRequestRepository,
)
from solarops.execution.infrastructure.in_memory_audit_log import InMemoryAuditLog
from solarops.execution.infrastructure.in_memory_command_repository import InMemoryCommandRepository
from solarops.platform.decision_wiring import build_operating_constraints
from solarops.platform.safety_wiring import build_policy, build_safety_limits
from solarops.platform.twin_hardware_interface import SimulatedHardwareInterface
from solarops.platform.twin_telemetry_source import TwinTelemetrySource
from solarops.safety.application.policy_validator import PolicyValidator
from solarops.safety.application.risk_assessor import RiskAssessor
from solarops.safety.application.safety_validator import SafetyValidator
from solarops.safety.infrastructure.in_memory_policy_repository import InMemoryPolicyRepository
from solarops.safety.infrastructure.static_safety_limits_provider import StaticSafetyLimitsProvider
from solarops.shared_kernel import FixedClock, SiteId
from solarops.simulation.domain.digital_twin import DigitalTwin
from solarops.simulation.infrastructure.config import SimulatorConfig, SiteConfig
from solarops.telemetry.application.ingestion_service import TelemetryIngestionService
from solarops.telemetry.application.state_manager import StateManager
from solarops.telemetry.infrastructure.in_memory_state_store import InMemoryStateStore

SITE_ID = SiteId("site-001")


def main() -> None:
    # --- Simulation + Telemetry (Phases 2-3) ---
    # battery_max_charge_kw raised well above the real engine's natural
    # solar-surplus recommendation (~55kW at this simulated noon) so it stays
    # comfortably under RiskAssessor's 50%-of-rated "large power swing"
    # threshold — this script demonstrates the LOW-risk, auto-approved path.
    site_config = SiteConfig(
        site_id="site-001",
        update_interval_seconds=300,
        battery_starting_soc_pct=50.0,
        battery_max_charge_kw=200.0,
    )
    twin = DigitalTwin(
        site_config=site_config,
        simulator_config=SimulatorConfig(random_seed=42),
        start_time=datetime(2026, 7, 25, 12, 0),
    )
    telemetry_source = TwinTelemetrySource(twin)
    clock = FixedClock(datetime(2026, 7, 25, 12, 0, tzinfo=UTC))
    ingestion = TelemetryIngestionService(telemetry_source, clock)
    state_store = InMemoryStateStore()
    state_manager = StateManager(state_store)

    def refresh_telemetry() -> None:
        state, _events = ingestion.ingest(SITE_ID)
        state_manager.update(state)

    refresh_telemetry()  # initial reading, before any command

    # --- Safety (Phase 5, Part A) — built first so Decision (below) can read
    # the same real Policy/SafetyLimits as OperatingConstraints (read-only). ---
    policy = build_policy(site_config)
    safety_limits = build_safety_limits(site_config)
    policy_repository = InMemoryPolicyRepository()
    policy_repository.save(policy)
    limits_provider = StaticSafetyLimitsProvider(safety_limits)
    policy_validator = PolicyValidator(policy_repository, clock)
    safety_validator = SafetyValidator(limits_provider, state_store, clock)
    risk_assessor = RiskAssessor(clock)

    # --- Decision (Phase 6c: real v1 rule engine) ---
    operating_constraints = build_operating_constraints(policy, safety_limits)
    engine = RuleBasedOptimiser(RuleEngineConfig(), clock)
    context = DecisionContext(
        energy_state=state_store.get(SITE_ID), operating_constraints=operating_constraints
    )
    ranked = engine.recommend(context)
    recommendation = ranked.top
    print(
        f"Recommendation: {recommendation.action} params={recommendation.params} "
        f"confidence={recommendation.confidence:.0%}"
    )
    print(f"  why:      {recommendation.reason}")
    print(f"  why_now:  {recommendation.why_now}")
    print(f"  evidence: {recommendation.evidence}")

    # --- Execution (Phase 5, Part B) ---
    hardware = SimulatedHardwareInterface(twin)
    approval_repository = InMemoryApprovalRequestRepository()
    pipeline = ExecutionPipeline(
        command_planner=CommandPlanner(clock),
        policy_validator=policy_validator,
        safety_validator=safety_validator,
        risk_assessor=risk_assessor,
        approval_engine=ApprovalEngine(approval_repository, clock),
        execution_manager=ExecutionManager(hardware, clock),
        verification_service=VerificationService(state_manager, clock),
        command_repository=InMemoryCommandRepository(),
        approval_repository=approval_repository,
        audit_log=InMemoryAuditLog(),
        state_store=state_store,
        policy_repository=policy_repository,
        safety_limits_provider=limits_provider,
        clock=clock,
        telemetry_refresh=refresh_telemetry,
    )

    command = pipeline.run(recommendation)

    execution_outcome = command.execution_result.outcome if command.execution_result else None
    verification = command.verification_result
    verification_passed = verification.passed if verification else None
    print(f"\n=== Command {command.command_id} ===")
    print(f"  final status:  {command.status}")
    print(f"  execution:     {execution_outcome}")
    print(f"  verification:  passed={verification_passed}")
    if command.verification_result:
        print(f"    expected: {command.verification_result.expected}")
        print(f"    observed: {command.verification_result.observed}")
    print(f"\nCommand is COMPLETED: {command.status.is_success}")


if __name__ == "__main__":
    main()
