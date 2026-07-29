from solarops.platform.forecast_wiring import (
    build_forecast_config,
    build_twin_benchmark_scenario_source,
    build_twin_historical_data_source,
    forecast_site_config,
)
from solarops.simulation.infrastructure.config import SiteConfig


def test_build_forecast_config_reuses_site_config_numbers():
    site_config = SiteConfig(site_id="site-001")
    config = build_forecast_config(site_config)

    assert config.site_id == "site-001"
    assert config.battery_capacity_kwh == site_config.battery_capacity_kwh
    assert config.battery_round_trip_efficiency == site_config.battery_round_trip_efficiency
    assert config.solar_capacity_kw == site_config.solar_capacity_kw


def test_forecast_site_config_overrides_only_the_tick_interval():
    site_config = SiteConfig(site_id="site-001")
    fast_config = forecast_site_config(site_config, resolution_minutes=15)

    assert fast_config.update_interval_seconds == 900
    assert fast_config.site_id == site_config.site_id
    assert fast_config.battery_capacity_kwh == site_config.battery_capacity_kwh


def test_build_twin_historical_data_source_is_wired_at_forecast_resolution():
    site_config = SiteConfig(site_id="site-001")
    config = build_forecast_config(site_config)
    source = build_twin_historical_data_source(site_config, config)

    assert source._site_config.update_interval_seconds == config.resolution_minutes * 60


def test_build_twin_benchmark_scenario_source_returns_all_six_scenarios():
    site_config = SiteConfig(site_id="site-001")
    config = build_forecast_config(site_config)
    source = build_twin_benchmark_scenario_source(site_config, config)

    assert len(source.scenario_names()) == 6
