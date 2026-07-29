"""Ports the Telemetry context depends on.

Defined in domain, implemented in infrastructure (Doc 8 §9.1).
"""

from __future__ import annotations

from typing import Protocol

from solarops.shared_kernel import AssetId, SiteId
from solarops.telemetry.domain.asset import Asset
from solarops.telemetry.domain.energy_state import EnergyState
from solarops.telemetry.domain.telemetry import Telemetry


class TelemetrySource(Protocol):
    """Something that can produce the latest reading for a site.

    Implemented by the platform-layer twin adapter today; a real ingestion
    endpoint (MQTT/HTTP) implements the same Protocol tomorrow.
    """

    def read(self, site_id: SiteId) -> Telemetry: ...


class StateStore(Protocol):
    """Layer 1 working memory: the current ``EnergyState`` per site."""

    def get(self, site_id: SiteId) -> EnergyState | None: ...

    def set(self, state: EnergyState) -> None: ...


class AssetRepository(Protocol):
    """The site's asset registry. No infrastructure implements this yet."""

    def get(self, asset_id: AssetId) -> Asset | None: ...

    def list_by_site(self, site_id: SiteId) -> list[Asset]: ...
