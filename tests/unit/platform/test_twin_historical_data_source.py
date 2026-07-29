from datetime import UTC, datetime, timedelta

import pytest

from solarops.platform.twin_historical_data_source import TwinHistoricalDataSource
from solarops.shared_kernel import SiteId
from solarops.simulation.infrastructure.config import SiteConfig

AS_OF = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)


def make_source(**site_overrides) -> TwinHistoricalDataSource:
    site_config = SiteConfig(site_id="site-001", update_interval_seconds=900, **site_overrides)
    return TwinHistoricalDataSource(site_config)


def test_produces_history_covering_the_lookback_window():
    source = make_source()
    history = source.get_history(SiteId("site-001"), as_of=AS_OF, lookback=timedelta(hours=6))
    assert len(history) == 24  # 6h / 15min


def test_history_is_ordered_and_timezone_aware():
    source = make_source()
    history = source.get_history(SiteId("site-001"), as_of=AS_OF, lookback=timedelta(hours=2))
    timestamps = [state.timestamp for state in history]
    assert timestamps == sorted(timestamps)
    assert all(ts.tzinfo is not None for ts in timestamps)


def test_rejects_mismatched_site_id():
    source = make_source()
    with pytest.raises(ValueError, match="site-001"):
        source.get_history(SiteId("some-other-site"), as_of=AS_OF, lookback=timedelta(hours=1))


def test_net_power_and_offline_are_populated():
    source = make_source()
    history = source.get_history(SiteId("site-001"), as_of=AS_OF, lookback=timedelta(hours=1))
    for state in history:
        assert state.net_power.value == pytest.approx(
            state.solar_power.value - state.building_load.value
        )
        assert state.any_asset_offline is False
