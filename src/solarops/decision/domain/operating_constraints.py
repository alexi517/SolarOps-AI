"""OperatingConstraints — Decision's own read-only view of the site's active
operating limits (Phase 6c brief §3).

Decision's import contract permits `shared_kernel`, `telemetry`, and
`forecast` only — never `safety` (`Policy`/`SafetyLimits` are Safety types).
This VO is Decision's own copy of exactly the numbers it needs to reason
*sensibly* (not authoritatively — Safety independently re-derives and
re-checks everything from `SiteConfig` itself; there is no overlap in
authority, only Decision getting realistic inputs). Populated at the platform
composition root from the real `Policy`/`SafetyLimits` objects
(`platform/decision_wiring.py`), mirroring how Forecast keeps its own copy of
`SiteConfig`'s battery parameters (Phase 6a).
"""

from __future__ import annotations

from dataclasses import dataclass

from solarops.shared_kernel import Power, StateOfCharge, Temperature

__all__ = ["OperatingConstraints"]


@dataclass(frozen=True, slots=True)
class OperatingConstraints:
    max_battery_soc: StateOfCharge
    min_battery_soc: StateOfCharge
    battery_max_temp: Temperature
    battery_max_charge_power: Power
    battery_max_discharge_power: Power
    maintenance_mode: bool
    max_shed_fraction: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.max_shed_fraction <= 1.0:
            raise ValueError(
                f"max_shed_fraction must be within [0, 1], got {self.max_shed_fraction}"
            )
