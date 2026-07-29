"""Ports the Safety context depends on.

Defined in domain, implemented in infrastructure (Doc 8 §9.1).
"""

from __future__ import annotations

from typing import Protocol

from solarops.safety.domain.policy import Policy
from solarops.safety.domain.safety_limits import SafetyLimits
from solarops.shared_kernel import SiteId


class PolicyRepository(Protocol):
    def get_current(self, site_id: SiteId) -> Policy | None: ...

    def save(self, policy: Policy) -> None: ...


class SafetyLimitsProvider(Protocol):
    def get_limits(self, site_id: SiteId) -> SafetyLimits | None: ...
