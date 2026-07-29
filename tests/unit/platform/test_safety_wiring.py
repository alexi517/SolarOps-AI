from solarops.platform.safety_wiring import build_policy, build_safety_limits
from solarops.shared_kernel import GridStatus, InverterStatus, SiteId
from solarops.simulation.infrastructure.config import SiteConfig


def test_build_policy_reuses_site_config_soc_targets():
    site_config = SiteConfig(site_id="site-001")
    policy = build_policy(site_config)

    assert policy.site_id == SiteId("site-001")
    assert policy.max_battery_soc.value == site_config.battery_max_soc_pct
    assert policy.min_battery_soc.value == site_config.battery_min_soc_pct
    assert policy.maintenance_mode is False
    assert policy.max_shed_fraction == 0.0


def test_build_safety_limits_reuses_site_config_numbers():
    site_config = SiteConfig(site_id="site-001")
    limits = build_safety_limits(site_config)

    assert limits.battery_min_soc.value == site_config.battery_min_soc_pct
    assert limits.battery_max_soc.value == site_config.battery_max_soc_pct
    assert limits.battery_max_temp.value == site_config.battery_max_temp_c
    assert limits.battery_max_charge_power.value == site_config.battery_max_charge_kw
    assert limits.battery_max_discharge_power.value == site_config.battery_max_discharge_kw
    assert limits.inverter_max_power.value == site_config.inverter_rated_capacity_kw
    assert limits.inverter_allowed_statuses == frozenset({InverterStatus.NORMAL})
    assert limits.grid_required_status is GridStatus.CONNECTED
    assert limits.grid_nominal_voltage.value == site_config.grid_nominal_voltage_v
    assert limits.grid_voltage_tolerance.value == site_config.grid_voltage_tolerance_v
    assert limits.grid_nominal_frequency.value == site_config.grid_nominal_frequency_hz
    assert limits.grid_frequency_tolerance.value == site_config.grid_frequency_tolerance_hz
