from datetime import UTC, datetime, timedelta

from solarops.forecast.infrastructure.historical_data_source import InMemoryHistoricalDataSource
from solarops.shared_kernel import SiteId
from solarops.telemetry.domain.energy_state import EnergyState

from ...telemetry.domain.test_telemetry import make_telemetry

SITE_ID = SiteId("SITE-1")
OTHER_SITE = SiteId("SITE-2")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_state(site_id=SITE_ID, **overrides) -> EnergyState:
    telemetry = make_telemetry(site_id=site_id, **overrides)
    return EnergyState.from_telemetry(telemetry, any_asset_offline=False)


def test_returns_only_states_within_lookback_window():
    source = InMemoryHistoricalDataSource()
    source.add(make_state(timestamp=NOW - timedelta(hours=5)))
    in_window = make_state(timestamp=NOW - timedelta(hours=1))
    source.add(in_window)
    source.add(make_state(timestamp=NOW))

    history = source.get_history(SITE_ID, as_of=NOW, lookback=timedelta(hours=2))

    assert history == [in_window, make_state(timestamp=NOW)]


def test_returns_states_ordered_by_timestamp():
    source = InMemoryHistoricalDataSource()
    later = make_state(timestamp=NOW)
    earlier = make_state(timestamp=NOW - timedelta(minutes=30))
    source.add(later)
    source.add(earlier)

    history = source.get_history(SITE_ID, as_of=NOW, lookback=timedelta(hours=1))

    assert history == [earlier, later]


def test_scoped_per_site():
    source = InMemoryHistoricalDataSource()
    source.add(make_state(site_id=OTHER_SITE, timestamp=NOW))

    history = source.get_history(SITE_ID, as_of=NOW, lookback=timedelta(hours=1))

    assert history == []


def test_constructor_accepts_initial_history():
    state = make_state(timestamp=NOW)
    source = InMemoryHistoricalDataSource([state])

    history = source.get_history(SITE_ID, as_of=NOW, lookback=timedelta(hours=1))

    assert history == [state]
