"""Policy — aggregate root, the site's configurable *operational* rules (Doc 8 §6.4).

Distinct from ``SafetyLimits`` (safety_limits.py): Policy can say "no" and an
operator can relax it; nothing relaxes SafetyLimits (see A.1 of the Phase 5
brief). "Versioned" here means a new ``Policy`` instance replaces the old one
via ``PolicyRepository.save()`` — this object itself stays an immutable
snapshot, consistent with every other aggregate in this codebase (``Asset``,
``Scenario``).
"""

from __future__ import annotations

from dataclasses import dataclass

from solarops.shared_kernel import PolicyId, SiteId, StateOfCharge

__all__ = ["Policy"]


@dataclass(frozen=True, slots=True)
class Policy:
    policy_id: PolicyId
    site_id: SiteId
    version: int

    max_battery_soc: StateOfCharge
    min_battery_soc: StateOfCharge

    maintenance_mode: bool = False
    # Lets an operator permit actions during maintenance mode without
    # disabling maintenance mode itself (e.g. a supervised manual test).
    maintenance_override: bool = False

    # Ceiling on load-shedding (v1 stand-in for per-load critical-load
    # protection — see the Phase 5 brief's "Critical loads" resolution).
    # 0.0 (default) means load-shedding is disabled entirely.
    max_shed_fraction: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.max_shed_fraction <= 1.0:
            raise ValueError(
                f"max_shed_fraction must be within [0, 1], got {self.max_shed_fraction}"
            )
