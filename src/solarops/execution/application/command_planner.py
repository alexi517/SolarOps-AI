"""CommandPlanner — Recommendation -> Command (Doc 8 §6.5, CESF §5).

Assigns a unique command ID (via ``Command.create``), an idempotency key, a
trace ID, and a timestamp. ``CREATED -> PLANNED`` is folded into
``Command.create()`` — see that method's docstring.

There is no asset registry yet (``AssetRepository`` remains a port with no
implementation — a seam disclosed since Phase 3). ``_resolve_asset_id`` is an
explicit, documented stand-in: one asset per action's natural kind, not a real
lookup. Flagged the same way as every other disclosed gap this phase.
"""

from __future__ import annotations

from uuid import uuid4

from solarops.decision.domain.recommendation import Recommendation
from solarops.execution.domain.command import Command
from solarops.execution.domain.events import CommandCreated
from solarops.shared_kernel import ActionType, AssetId, Clock, SiteId

__all__ = ["CommandPlanner"]

_ACTION_ASSET_KIND: dict[ActionType, str] = {
    ActionType.CHARGE_BATTERY: "battery",
    ActionType.DISCHARGE_BATTERY: "battery",
    ActionType.HOLD_BATTERY: "battery",
    ActionType.CURTAIL_SOLAR: "solar",
    ActionType.IMPORT_FROM_GRID: "grid",
    ActionType.EXPORT_TO_GRID: "grid",
    ActionType.SET_INVERTER_MODE: "inverter",
    ActionType.SHED_LOAD: "building-load",
    ActionType.RESTORE_LOAD: "building-load",
    ActionType.NO_OP: "site",
}


class CommandPlanner:
    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def plan(
        self, recommendation: Recommendation, *, trace_id: str | None = None
    ) -> tuple[Command, CommandCreated]:
        command = Command.create(
            site_id=recommendation.site_id,
            asset_id=self._resolve_asset_id(recommendation.site_id, recommendation.action),
            recommendation_id=recommendation.recommendation_id,
            action=recommendation.action,
            params=recommendation.params,
            idempotency_key=f"idem-{recommendation.recommendation_id}",
            trace_id=trace_id or str(uuid4()),
            created_at=self._clock.now(),
        )
        event = CommandCreated(
            aggregate_id=str(command.command_id),
            aggregate_type="Command",
            action=command.action,
            idempotency_key=command.idempotency_key,
        )
        return command, event

    @staticmethod
    def _resolve_asset_id(site_id: SiteId, action: ActionType) -> AssetId:
        kind = _ACTION_ASSET_KIND.get(action, "site")
        return AssetId(f"{site_id}-{kind}")
