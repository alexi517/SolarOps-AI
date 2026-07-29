"""Builds Decision's ``OperatingConstraints`` from the real Safety objects.

Composition root: the one place allowed to import both ``safety`` (for
``Policy``/``SafetyLimits``) and ``decision`` (for ``OperatingConstraints``) —
Decision itself never imports Safety (see
``decision/domain/operating_constraints.py``'s docstring). Projects the
already-built ``Policy``/``SafetyLimits`` (``platform/safety_wiring.py``)
rather than recomputing from ``SiteConfig`` a second time, so Decision's view
can never silently drift from what Safety actually enforces.
"""

from __future__ import annotations

from solarops.decision.domain.operating_constraints import OperatingConstraints
from solarops.safety.domain.policy import Policy
from solarops.safety.domain.safety_limits import SafetyLimits

__all__ = ["build_operating_constraints"]


def build_operating_constraints(
    policy: Policy, safety_limits: SafetyLimits
) -> OperatingConstraints:
    return OperatingConstraints(
        max_battery_soc=policy.max_battery_soc,
        min_battery_soc=policy.min_battery_soc,
        battery_max_temp=safety_limits.battery_max_temp,
        battery_max_charge_power=safety_limits.battery_max_charge_power,
        battery_max_discharge_power=safety_limits.battery_max_discharge_power,
        maintenance_mode=policy.maintenance_mode,
        max_shed_fraction=policy.max_shed_fraction,
    )
