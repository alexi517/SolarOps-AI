"""Static SafetyLimitsProvider — one injected SafetyLimits, same for every site (v1: one site)."""

from __future__ import annotations

from solarops.safety.domain.safety_limits import SafetyLimits
from solarops.shared_kernel import SiteId


class StaticSafetyLimitsProvider:
    def __init__(self, limits: SafetyLimits) -> None:
        self._limits = limits

    def get_limits(self, site_id: SiteId) -> SafetyLimits | None:
        return self._limits
