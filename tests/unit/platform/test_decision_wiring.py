from solarops.platform.decision_wiring import build_operating_constraints
from solarops.platform.safety_wiring import build_policy, build_safety_limits
from solarops.simulation.infrastructure.config import SiteConfig


def test_build_operating_constraints_reuses_the_same_numbers_as_safety():
    site_config = SiteConfig(site_id="site-001")
    policy = build_policy(site_config)
    safety_limits = build_safety_limits(site_config)

    constraints = build_operating_constraints(policy, safety_limits)

    assert constraints.max_battery_soc == policy.max_battery_soc
    assert constraints.min_battery_soc == policy.min_battery_soc
    assert constraints.battery_max_temp == safety_limits.battery_max_temp
    assert constraints.battery_max_charge_power == safety_limits.battery_max_charge_power
    assert constraints.battery_max_discharge_power == safety_limits.battery_max_discharge_power
    assert constraints.maintenance_mode == policy.maintenance_mode
    assert constraints.max_shed_fraction == policy.max_shed_fraction
