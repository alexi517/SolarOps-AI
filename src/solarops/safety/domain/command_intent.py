"""CommandIntent — Safety's own minimal view of "an action being considered".

Not in the brief's Part A file list — added because the validators need *some*
input type, and Safety's import rule (shared kernel + Telemetry only) means
they cannot take Execution's ``Command`` aggregate as a parameter: Command
doesn't exist yet (Part B), and even once it does, Safety still can't import
Execution. ``command_id`` reuses the shared-kernel ``CommandId`` so this lines
up cleanly with the real ``Command`` aggregate Part B will build on the same ID.

``asset_operating_mode`` defaults to ``None`` ("unknown") — there is no
``AssetRepository`` infrastructure anywhere yet (a documented seam since
Phase 3), so nothing can look up an asset's real persisted operating mode.
Whoever constructs the intent may supply it if known; when it's
``AssetOperatingMode.EMERGENCY``, ``SafetyValidator`` blocks unconditionally.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from solarops.shared_kernel import ActionType, AssetId, AssetOperatingMode, CommandId, SiteId

__all__ = ["CommandIntent"]


@dataclass(frozen=True, slots=True)
class CommandIntent:
    command_id: CommandId
    site_id: SiteId
    asset_id: AssetId
    action: ActionType
    params: dict = field(default_factory=dict)
    asset_operating_mode: AssetOperatingMode | None = None
