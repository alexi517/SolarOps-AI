"""Builds AnomalyConfig and the twin-driven Anomaly adapters from SiteConfig.

Composition root: mirrors ``platform/forecast_wiring.py``'s pattern — numbers
come from the same ``SiteConfig`` the twin itself uses, never duplicated by
hand. Unlike Forecast's wiring, no tick-resolution override is applied: the
Detection Delay target (brief §5, <10s) needs the twin's natural fine-grained
tick, not a 15-minute one.
"""

from __future__ import annotations

from solarops.anomaly.infrastructure.config import AnomalyConfig
from solarops.platform.twin_fault_scenario_source import TwinFaultScenarioSource
from solarops.platform.twin_historical_data_source import TwinHistoricalDataSource
from solarops.simulation.infrastructure.config import SiteConfig

__all__ = [
    "build_anomaly_config",
    "build_twin_historical_data_source",
    "build_twin_fault_scenario_source",
]


def build_anomaly_config(site_config: SiteConfig) -> AnomalyConfig:
    return AnomalyConfig(
        site_id=site_config.site_id,
        battery_overheat_temp_c=site_config.battery_max_temp_c,
    )


def build_twin_historical_data_source(site_config: SiteConfig) -> TwinHistoricalDataSource:
    return TwinHistoricalDataSource(site_config)


def build_twin_fault_scenario_source(
    site_config: SiteConfig | None = None,
) -> TwinFaultScenarioSource:
    return TwinFaultScenarioSource(site_config)
