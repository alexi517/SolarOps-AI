import fakeredis

from solarops.shared_kernel import SiteId
from solarops.telemetry.domain.energy_state import EnergyState
from solarops.telemetry.infrastructure.redis_state_store import RedisStateStore

from ..domain.test_telemetry import make_telemetry

SITE_ID = SiteId("SITE-1")


def make_store() -> RedisStateStore:
    return RedisStateStore(fakeredis.FakeRedis())


def test_get_returns_none_when_key_absent():
    store = make_store()
    assert store.get(SITE_ID) is None


def test_set_then_get_round_trips_through_json():
    store = make_store()
    state = EnergyState.from_telemetry(make_telemetry(site_id=SITE_ID), any_asset_offline=False)

    store.set(state)
    fetched = store.get(SITE_ID)

    assert fetched == state


def test_states_for_different_sites_do_not_collide():
    store = make_store()
    telemetry_a = make_telemetry(site_id=SiteId("SITE-A"))
    telemetry_b = make_telemetry(site_id=SiteId("SITE-B"))
    state_a = EnergyState.from_telemetry(telemetry_a, any_asset_offline=False)
    state_b = EnergyState.from_telemetry(telemetry_b, any_asset_offline=True)

    store.set(state_a)
    store.set(state_b)

    assert store.get(SiteId("SITE-A")) == state_a
    assert store.get(SiteId("SITE-B")) == state_b
