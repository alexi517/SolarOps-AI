"""SafetyLimits — the hard physical limits (Doc 8 §6.4, §7). Never relaxed.

TODO(safety-limits-gap): battery current and inverter voltage/current are not
represented here. Neither has a backing field anywhere in the domain — the
Digital Twin's ``BatteryModel``/``InverterModel`` never computed or reported
them (only SOC/SOH/temp/power for the battery; power/temp/status for the
inverter). There is nothing to check against, so no threshold is invented.
Add these once the Simulation context's physics models are extended to
produce them (see the Phase 5 brief's "Unmeasurable limits" resolution).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from solarops.shared_kernel import (
    Frequency,
    GridStatus,
    InverterStatus,
    Power,
    StateOfCharge,
    Temperature,
    Voltage,
)

__all__ = ["SafetyLimits"]


@dataclass(frozen=True, slots=True)
class SafetyLimits:
    battery_min_soc: StateOfCharge
    battery_max_soc: StateOfCharge
    battery_max_temp: Temperature
    battery_max_charge_power: Power
    battery_max_discharge_power: Power

    inverter_max_power: Power
    inverter_allowed_statuses: frozenset[InverterStatus] = field(
        default_factory=lambda: frozenset({InverterStatus.NORMAL})
    )

    grid_required_status: GridStatus = GridStatus.CONNECTED
    grid_nominal_voltage: Voltage = field(default_factory=lambda: Voltage(415.0))
    grid_voltage_tolerance: Voltage = field(default_factory=lambda: Voltage(2.0))
    grid_nominal_frequency: Frequency = field(default_factory=lambda: Frequency(50.0))
    grid_frequency_tolerance: Frequency = field(default_factory=lambda: Frequency(0.05))

    # The hard ceiling on load-shedding — never relaxed, independent of
    # Policy.max_shed_fraction (the operator-configurable ceiling). Default
    # 0.0: no load may be shed unless this is deliberately raised. There is no
    # per-load critical/non-critical taxonomy anywhere in the domain (no model
    # supports it — BuildingLoadModel.shed_load() sheds uniformly), so this is
    # a site-wide "protect everything by default" stand-in for per-load
    # protection, not a per-load check.
    building_max_shed_fraction: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.building_max_shed_fraction <= 1.0:
            raise ValueError(
                "building_max_shed_fraction must be within [0, 1], got "
                f"{self.building_max_shed_fraction}"
            )
