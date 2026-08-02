"""AutoDecisionCycleScheduler — optional background loop that triggers
decision cycles on an interval, so a live deployment doesn't require a human
to click "Run decision cycle" for every routine cycle.

Off unless ``PlatformSettings.auto_decision_cycle_seconds`` is set > 0 (see
that field's own docstring for why the default is 0, not "on"). This only
decides whether the *cycle itself* runs without a human triggering it — the
existing risk-based auto-execute policy (``RiskLevel.is_auto_executable``)
still independently decides which resulting commands need approval; this
doesn't relax that at all, it just removes the need to click a button for
the routine, already-auto-executable cases.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from solarops.platform.api_composition import SystemComposition

__all__ = ["AutoDecisionCycleScheduler"]

logger = logging.getLogger(__name__)


class AutoDecisionCycleScheduler:
    def __init__(self, composition: SystemComposition, interval_seconds: float) -> None:
        self._composition = composition
        self._interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._interval_seconds <= 0 or self._task is not None:
            return
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self._interval_seconds)
            try:
                # run_decision_cycle() is synchronous and does real I/O
                # (telemetry, the execution pipeline) — off the event loop
                # via to_thread so it can't stall every other request while
                # it runs. Its own lock (SystemComposition._decision_cycle_lock)
                # keeps this from ever overlapping a manual trigger.
                await asyncio.to_thread(self._composition.run_decision_cycle)
            except asyncio.CancelledError:
                raise
            except Exception:
                # One bad cycle (a transient telemetry/network failure, say)
                # must not silently kill the loop — log it and try again next
                # interval, same fail-visible-not-fail-fatal spirit as the
                # rest of this codebase's error handling.
                logger.exception("Automatic decision cycle failed")
