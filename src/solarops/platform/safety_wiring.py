"""Builds Policy and SafetyLimits from SiteConfig (Phase 5 brief, A.4).

Composition root: imports both ``safety`` (for the types) and ``simulation``
(for ``SiteConfig``, so the numbers are read from the same configuration the
twin itself uses, never duplicated or invented separately). Safety itself
never imports simulation.
"""

from __future__ import annotations

from solarops.safety.domain.policy import Policy
from solarops.safety.domain.safety_limits import SafetyLimits
from solarops.shared_kernel import (
    Frequency,
    GridStatus,
    InverterStatus,
    PolicyId,
    Power,
    SiteId,
    StateOfCharge,
    Temperature,
    Voltage,
)
from solarops.simulation.infrastructure.config import SiteConfig

__all__ = ["build_policy", "build_safety_limits"]


def build_policy(site_config: SiteConfig) -> Policy:
    return Policy(
        policy_id=PolicyId.generate(),
        site_id=SiteId(site_config.site_id),
        version=1,
        max_battery_soc=StateOfCharge(site_config.battery_max_soc_pct),
        min_battery_soc=StateOfCharge(site_config.battery_min_soc_pct),
    )


def build_safety_limits(site_config: SiteConfig) -> SafetyLimits:
    return SafetyLimits(
        battery_min_soc=StateOfCharge(site_config.battery_min_soc_pct),
        battery_max_soc=StateOfCharge(site_config.battery_max_soc_pct),
        battery_max_temp=Temperature(site_config.battery_max_temp_c),
        battery_max_charge_power=Power(site_config.battery_max_charge_kw),
        battery_max_discharge_power=Power(site_config.battery_max_discharge_kw),
        inverter_max_power=Power(site_config.inverter_rated_capacity_kw),
        inverter_allowed_statuses=frozenset({InverterStatus.NORMAL}),
        grid_required_status=GridStatus.CONNECTED,
        grid_nominal_voltage=Voltage(site_config.grid_nominal_voltage_v),
        grid_voltage_tolerance=Voltage(site_config.grid_voltage_tolerance_v),
        grid_nominal_frequency=Frequency(site_config.grid_nominal_frequency_hz),
        grid_frequency_tolerance=Frequency(site_config.grid_frequency_tolerance_hz),
    )
