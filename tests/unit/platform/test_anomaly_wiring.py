from solarops.platform.anomaly_wiring import (
    build_anomaly_config,
    build_twin_fault_scenario_source,
    build_twin_historical_data_source,
)
from solarops.simulation.infrastructure.config import SiteConfig


def test_build_anomaly_config_reuses_site_config_numbers():
    site_config = SiteConfig(site_id="site-001")
    config = build_anomaly_config(site_config)

    assert config.site_id == "site-001"
    assert config.battery_overheat_temp_c == site_config.battery_max_temp_c


def test_build_twin_historical_data_source_keeps_fine_tick_resolution():
    site_config = SiteConfig(site_id="site-001", update_interval_seconds=5)
    source = build_twin_historical_data_source(site_config)
    assert source._site_config.update_interval_seconds == 5


def test_build_twin_fault_scenario_source_returns_all_five_scenarios():
    source = build_twin_fault_scenario_source(SiteConfig(site_id="site-001"))
    assert len(source.scenario_names()) == 5
