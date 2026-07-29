"""Asset — aggregate root (Document 8 §6.1).

The site's registry of controllable/observable units: identity, type, static
config, and current coarse operating mode. This is the *administrative* record
of an asset — distinct from the Simulation context's physics models, which
compute behaviour, not identity.

No infrastructure backs an ``AssetRepository`` yet (see ``ports.py``) — this
aggregate exists so ``EnergyState`` and future wiring aren't blocked, not
because persistence is implemented this phase.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from solarops.shared_kernel import AssetId, AssetOperatingMode, AssetType, SiteId


@dataclass(frozen=True, slots=True)
class Asset:
    asset_id: AssetId
    site_id: SiteId
    asset_type: AssetType
    operating_mode: AssetOperatingMode = AssetOperatingMode.NORMAL
    config: dict = field(default_factory=dict)
