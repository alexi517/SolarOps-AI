from solarops.shared_kernel import SiteId
from solarops.telemetry.application.state_manager import StateManager
from solarops.telemetry.domain.energy_state import EnergyState
from solarops.telemetry.domain.events import EnergyStateUpdated
from solarops.telemetry.infrastructure.in_memory_state_store import InMemoryStateStore

from ..domain.test_telemetry import make_telemetry

SITE_ID = SiteId("SITE-1")


def test_get_current_returns_none_when_no_state_yet():
    manager = StateManager(InMemoryStateStore())
    assert manager.get_current(SITE_ID) is None


def test_update_then_get_current_round_trips():
    manager = StateManager(InMemoryStateStore())
    state = EnergyState.from_telemetry(make_telemetry(site_id=SITE_ID), any_asset_offline=False)

    manager.update(state)

    assert manager.get_current(SITE_ID) == state


def test_update_emits_energy_state_updated():
    manager = StateManager(InMemoryStateStore())
    state = EnergyState.from_telemetry(make_telemetry(site_id=SITE_ID), any_asset_offline=False)

    event = manager.update(state)

    assert isinstance(event, EnergyStateUpdated)
    assert event.aggregate_id == str(SITE_ID)
    assert event.state_timestamp == state.timestamp
