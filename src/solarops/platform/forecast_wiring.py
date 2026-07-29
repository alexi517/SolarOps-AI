"""Builds ForecastConfig and the twin-driven Forecast adapters from SiteConfig.

Composition root: mirrors ``platform/safety_wiring.py``'s ``build_policy``/
``build_safety_limits`` pattern — the numbers come from the same ``SiteConfig``
the twin itself uses, never duplicated by hand.
"""

from __future__ import annotations

from solarops.forecast.infrastructure.config import ForecastConfig
from solarops.platform.benchmark_scenario_source import TwinBenchmarkScenarioSource
from solarops.platform.twin_historical_data_source import TwinHistoricalDataSource
from solarops.simulation.infrastructure.config import SiteConfig

__all__ = [
    "build_forecast_config",
    "forecast_site_config",
    "build_twin_historical_data_source",
    "build_twin_benchmark_scenario_source",
]


def build_forecast_config(site_config: SiteConfig) -> ForecastConfig:
    return ForecastConfig(
        site_id=site_config.site_id,
        battery_capacity_kwh=site_config.battery_capacity_kwh,
        battery_round_trip_efficiency=site_config.battery_round_trip_efficiency,
        solar_capacity_kw=site_config.solar_capacity_kw,
    )


def forecast_site_config(site_config: SiteConfig, resolution_minutes: int) -> SiteConfig:
    """A copy of ``site_config`` ticking at the forecast resolution, not the twin's 5s default.

    Forecasting works in 15-minute steps out to 6 hours; running the twin at
    its default 5-second physics tick for that horizon would take thousands of
    ticks per data point. The physical parameters are unchanged — only how
    often the twin advances.
    """
    return site_config.model_copy(update={"update_interval_seconds": resolution_minutes * 60})


def build_twin_historical_data_source(
    site_config: SiteConfig, config: ForecastConfig
) -> TwinHistoricalDataSource:
    return TwinHistoricalDataSource(forecast_site_config(site_config, config.resolution_minutes))


def build_twin_benchmark_scenario_source(
    site_config: SiteConfig, config: ForecastConfig
) -> TwinBenchmarkScenarioSource:
    return TwinBenchmarkScenarioSource(
        config, forecast_site_config(site_config, config.resolution_minutes)
    )
