"""Smoke test: real EnergyState -> LangGraph -> real RuleBasedOptimiser -> explained Recommendation.

Phase 6c end-to-end: Digital Twin -> TwinTelemetrySource -> ingestion ->
StateManager (Phase 3, unchanged) -> StateManager.get_current() -> the
LangGraph graph, now backed by the real v1 rule engine (Phase 6c) instead of
the Phase 4 stub. The EnergyState the graph consumes comes from the real
StateManager, not a fabricated one.
"""

from datetime import UTC, datetime, timedelta

from solarops.decision.application.rule_based_optimiser import RuleBasedOptimiser
from solarops.decision.infrastructure.config import RuleEngineConfig
from solarops.platform.decision_wiring import build_operating_constraints
from solarops.platform.safety_wiring import build_policy, build_safety_limits
from solarops.platform.twin_telemetry_source import TwinTelemetrySource
from solarops.shared_kernel import FixedClock, SiteId
from solarops.simulation.domain.digital_twin import DigitalTwin
from solarops.simulation.infrastructure.config import SimulatorConfig, SiteConfig
from solarops.telemetry.application.ingestion_service import TelemetryIngestionService
from solarops.telemetry.application.state_manager import StateManager
from solarops.telemetry.infrastructure.in_memory_state_store import InMemoryStateStore
from solarops.workflow.graph import build_graph

SITE_ID = SiteId("site-001")


def main() -> None:
    site_config = SiteConfig(site_id="site-001", update_interval_seconds=300)
    twin = DigitalTwin(
        site_config=site_config,
        simulator_config=SimulatorConfig(random_seed=42),
        start_time=datetime(2026, 7, 25, 6, 0),
    )
    source = TwinTelemetrySource(twin)
    clock = FixedClock(datetime(2026, 7, 25, 6, 0, tzinfo=UTC))
    interval = timedelta(seconds=twin.site_config.update_interval_seconds)
    ingestion = TelemetryIngestionService(source, clock)
    state_manager = StateManager(InMemoryStateStore())

    print("=== Decision pipeline: Twin -> EnergyState -> LangGraph -> RuleBasedOptimiser ===")

    # A few ticks so StateManager holds a real, current EnergyState — same
    # pattern as run_telemetry_pipeline.py (Phase 3).
    for _ in range(3):
        state, _events = ingestion.ingest(SITE_ID)
        state_manager.update(state)
        clock.advance(interval)

    current_state = state_manager.get_current(SITE_ID)
    print(
        f"\nReal EnergyState from StateManager: {current_state.timestamp} "
        f"— solar={current_state.solar_power.value:.1f}kW, "
        f"battery_soc={current_state.battery_soc.value:.1f}%"
    )

    operating_constraints = build_operating_constraints(
        build_policy(site_config), build_safety_limits(site_config)
    )
    engine = RuleBasedOptimiser(RuleEngineConfig(), clock)
    graph = build_graph(engine, operating_constraints)
    result = graph.invoke({"energy_state": current_state})
    recommendation = result["recommendation"]

    print("\n=== Recommendation (real v1 rule engine, Phase 6c) ===")
    print(f"  action:            {recommendation.action}")
    print(f"  params:            {recommendation.params}")
    print(f"  confidence:        {recommendation.confidence:.0%}")
    print(f"  expected_benefit:  {recommendation.expected_benefit}")
    print(f"  reason (why):      {recommendation.reason}")
    print(f"  why_now:           {recommendation.why_now}")
    print(f"  evidence:          {recommendation.evidence}")
    print(f"  alternatives:      {recommendation.alternatives}")
    print(f"  risks:             {recommendation.risks}")
    print(f"  generated_at:      {recommendation.generated_at}")


if __name__ == "__main__":
    main()
