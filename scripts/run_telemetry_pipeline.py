"""Smoke test: Digital Twin -> TwinTelemetrySource -> ingestion -> StateManager.

Confirms the whole Phase 3 path works end-to-end, not just in isolation per
layer: each tick's SimulationState becomes a Telemetry reading (platform
adapter), which the Telemetry context turns into an EnergyState held in Redis-
backed (here, in-memory) working memory, with events raised along the way.
"""

from datetime import UTC, datetime, timedelta

from solarops.platform.twin_telemetry_source import TwinTelemetrySource
from solarops.shared_kernel import FixedClock, SiteId
from solarops.simulation.domain.digital_twin import DigitalTwin
from solarops.simulation.infrastructure.config import SimulatorConfig, SiteConfig
from solarops.telemetry.application.ingestion_service import TelemetryIngestionService
from solarops.telemetry.application.state_manager import StateManager
from solarops.telemetry.infrastructure.in_memory_state_store import InMemoryStateStore

SITE_ID = SiteId("site-001")


def main() -> None:
    twin = DigitalTwin(
        site_config=SiteConfig(site_id="site-001", update_interval_seconds=300),
        simulator_config=SimulatorConfig(random_seed=42),
        start_time=datetime(2026, 7, 25, 6, 0),
    )
    source = TwinTelemetrySource(twin)

    # A FixedClock kept in lock-step with the twin's simulated time — mirrors a
    # live feed, where "now" tracks the latest reading rather than drifting
    # against unrelated wall-clock time.
    clock = FixedClock(datetime(2026, 7, 25, 6, 0, tzinfo=UTC))
    interval = timedelta(seconds=twin.site_config.update_interval_seconds)
    ingestion = TelemetryIngestionService(source, clock)
    state_manager = StateManager(InMemoryStateStore())

    print("=== Telemetry pipeline smoke test: Twin -> EnergyState ===")
    for step in range(6):
        state, events = ingestion.ingest(SITE_ID)
        update_event = state_manager.update(state)
        clock.advance(interval)

        print(f"\n[tick {step}] {state.timestamp.strftime('%H:%M')} UTC")
        print(
            f"  solar={state.solar_power.value:6.1f}kW  "
            f"battery_soc={state.battery_soc.value:5.1f}%  "
            f"net_power={state.net_power.value:6.1f}kW  offline={state.any_asset_offline}"
        )
        print(f"  events: {[type(e).__name__ for e in events]} + {type(update_event).__name__}")

    current = state_manager.get_current(SITE_ID)
    print("\n=== StateManager.get_current() ===")
    print(f"{current.timestamp} — solar={current.solar_power}")


if __name__ == "__main__":
    main()
