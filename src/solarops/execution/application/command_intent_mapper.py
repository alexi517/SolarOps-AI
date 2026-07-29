"""The single place a Command becomes a Safety CommandIntent.

Every call into PolicyValidator/SafetyValidator/RiskAssessor goes through
``to_command_intent`` — one mapping, one source of truth, so the two aggregates
(``Command`` and Safety's own ``CommandIntent``) can never silently drift apart.
"""

from __future__ import annotations

from solarops.execution.domain.command import Command
from solarops.safety.domain.command_intent import CommandIntent
from solarops.shared_kernel import AssetOperatingMode

__all__ = ["to_command_intent"]


def to_command_intent(
    command: Command, *, asset_operating_mode: AssetOperatingMode | None = None
) -> CommandIntent:
    return CommandIntent(
        command_id=command.command_id,
        site_id=command.site_id,
        asset_id=command.asset_id,
        action=command.action,
        params=command.params,
        asset_operating_mode=asset_operating_mode,
    )
