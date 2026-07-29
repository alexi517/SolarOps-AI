"""Smoke test: an unsafe command is blocked at the safety gate and never reaches the twin.

Phase 6c update: the Phase 4 stub always recommended ``CHARGE_BATTERY``
regardless of state, so parking the battery at max SOC was enough to make it
unsafe. The real v1 rule engine (Phase 6c) is itself safety-aware for SOC/
temperature/maintenance — it would no longer propose charging at max SOC, so
that scenario no longer demonstrates anything. This is exactly why the
architecture has two independent layers (brief §5 note, "two layers, on
purpose"): Decision's ``OperatingConstraints`` don't model inverter health at
all, so an inverter fault is invisible to it — the engine still recommends
``CHARGE_BATTERY`` off a genuine solar surplus, and Safety's independent,
more complete ``SafetyValidator`` (which *does* check inverter status)
catches what Decision's simpler judgment missed.
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
    # Normal SOC and a real solar surplus — the engine has every reason to
    # recommend CHARGE_BATTERY. The inverter fault, injected below, is what
    # makes that recommendation unsafe, and it's invisible to Decision.
    site_config = SiteConfig(
        site_id="site-001",
        update_interval_seconds=300,
        battery_starting_soc_pct=50.0,
        battery_max_charge_kw=100.0,
    )
    twin = DigitalTwin(
        site_config=site_config,
        simulator_config=SimulatorConfig(random_seed=42),
        start_time=datetime(2026, 7, 25, 12, 0),
    )
    twin.inject_fault("inverter", "FAULT_OVERTEMP")

    telemetry_source = TwinTelemetrySource(twin)
    clock = FixedClock(datetime(2026, 7, 25, 12, 0, tzinfo=UTC))
    ingestion = TelemetryIngestionService(telemetry_source, clock)
    state_store = InMemoryStateStore()
    state_manager = StateManager(state_store)

    def refresh_telemetry() -> None:
        state, _events = ingestion.ingest(SITE_ID)
        state_manager.update(state)

    refresh_telemetry()
    before = state_store.get(SITE_ID)
    print(
        f"Before: battery_soc={before.battery_soc.value:.1f}%  "
        f"inverter_status={before.inverter_status}  "
        f"solar={before.solar_power.value:.1f}kW  load={before.building_load.value:.1f}kW"
    )

    # --- Safety (built first so Decision can read the same real numbers) ---
    policy = build_policy(site_config)
    safety_limits = build_safety_limits(site_config)
    policy_repository = InMemoryPolicyRepository()
    policy_repository.save(policy)
    limits_provider = StaticSafetyLimitsProvider(safety_limits)

    # --- Decision (Phase 6c real engine) — genuinely unaware of the inverter fault ---
    operating_constraints = build_operating_constraints(policy, safety_limits)
    engine = RuleBasedOptimiser(RuleEngineConfig(), clock)
    context = DecisionContext(energy_state=before, operating_constraints=operating_constraints)
    recommendation = engine.recommend(context).top
    print(f"\nRecommendation: {recommendation.action} params={recommendation.params}")
    print(f"  why: {recommendation.reason}")

    hardware = SimulatedHardwareInterface(twin)
    approval_repository = InMemoryApprovalRequestRepository()

    pipeline = ExecutionPipeline(
        command_planner=CommandPlanner(clock),
        policy_validator=PolicyValidator(policy_repository, clock),
        safety_validator=SafetyValidator(limits_provider, state_store, clock),
        risk_assessor=RiskAssessor(clock),
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

    print(f"\n=== Command {command.command_id} ===")
    print(f"  final status: {command.status}")
    print(f"  safety_assessment.passed: {command.safety_assessment.passed}")
    print(f"  safety_assessment.failed_checks: {command.safety_assessment.failed_checks}")
    print(f"  execution_result: {command.execution_result}  (None = dispatch never attempted)")

    refresh_telemetry()
    after = state_store.get(SITE_ID)
    print(
        f"\nAfter:  battery_soc={after.battery_soc.value:.1f}%  battery_mode={after.battery_mode}"
    )
    print(f"Twin state unchanged (never reached): {before.battery_soc == after.battery_soc}")


if __name__ == "__main__":
    main()
