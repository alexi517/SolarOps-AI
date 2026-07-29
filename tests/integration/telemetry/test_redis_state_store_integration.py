"""Integration test against a real Redis instance.

Requires Redis on localhost:6379 (see docker-compose.yml: `docker compose up redis`).
Self-skips when no server is reachable, so `pytest` still passes without Docker.
"""

import pytest
import redis
from redis.backoff import NoBackoff
from redis.retry import Retry

from solarops.shared_kernel import SiteId
from solarops.telemetry.domain.energy_state import EnergyState
from solarops.telemetry.infrastructure.redis_state_store import RedisStateStore

from ...unit.telemetry.domain.test_telemetry import make_telemetry

SITE_ID = SiteId("SITE-integration-test")


@pytest.fixture
def redis_client():
    client = redis.Redis(
        host="localhost",
        port=6379,
        db=0,
        socket_connect_timeout=1,
        retry=Retry(NoBackoff(), retries=0),
    )
    try:
        client.ping()
    except redis.exceptions.RedisError:
        pytest.skip(
            "Redis is not reachable on localhost:6379 — start it with `docker compose up redis`"
        )
    yield client
    client.delete(f"state:{SITE_ID}")


def test_set_then_get_round_trips_through_real_redis(redis_client):
    store = RedisStateStore(redis_client)
    state = EnergyState.from_telemetry(make_telemetry(site_id=SITE_ID), any_asset_offline=False)

    store.set(state)
    fetched = store.get(SITE_ID)

    assert fetched == state
