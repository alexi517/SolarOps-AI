"""In-memory PolicyRepository — for tests and v1 (single-process, no persistence)."""

from __future__ import annotations

from solarops.safety.domain.policy import Policy
from solarops.shared_kernel import SiteId


class InMemoryPolicyRepository:
    def __init__(self) -> None:
        self._policies: dict[str, Policy] = {}

    def get_current(self, site_id: SiteId) -> Policy | None:
        return self._policies.get(str(site_id))

    def save(self, policy: Policy) -> None:
        self._policies[str(policy.site_id)] = policy
